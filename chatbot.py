import os
import json
import chromadb
import argparse
from chromadb.utils import embedding_functions
from tqdm import tqdm
from google import genai
import os
import subprocess
import openai
import sys
from dotenv import load_dotenv
import re

# Load environment variables (for API keys)
load_dotenv()

class PdfChatbot:
    def __init__(self, content_dir=None, model_name="gemini-pro", use_chroma=True):
        """
        Initialize the chatbot with a given content directory
        
        Args:
            content_dir: Directory containing extracted PDF content
            model_name: Name of the Gemini model to use
            use_chroma: Whether to use ChromaDB for vector storage
        """
        self.content_dir = self._find_content_dir(content_dir)
        self.chunks = []
        self.use_chroma = use_chroma
        self.chat_history = []
        self.model_name = model_name
        
        # Setup Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables. "
                            "Please add it to a .env file or set it in your environment.")
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)
        print(f"Initialized Gemini client for model: {model_name}")
        
        # Setup ChromaDB
        self._setup_chromadb()
        
        # Load chunks
        self.load_chunks()
        
        print(f"Chatbot initialized with {len(self.chunks)} chunks ready for context")
    
    def _find_content_dir(self, content_dir=None):
        """Find content directory if not specified"""
        if content_dir and os.path.exists(content_dir):
            return content_dir
            
        # Look for directories that match the pattern "extracted_content_*"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        potential_dirs = []
        
        for item in os.listdir(current_dir):
            if os.path.isdir(os.path.join(current_dir, item)) and item.startswith("extracted_content_"):
                potential_dirs.append(os.path.join(current_dir, item))
                
        if not potential_dirs:
            raise FileNotFoundError("No extracted content directories found. Please process a PDF first.")
            
        if len(potential_dirs) == 1:
            print(f"Using content directory: {potential_dirs[0]}")
            return potential_dirs[0]
            
        # If multiple directories, ask the user to select one
        print("Multiple content directories found. Please select one:")
        for i, directory in enumerate(potential_dirs):
            print(f"[{i+1}] {os.path.basename(directory)}")
            
        selection = None
        while selection is None:
            try:
                idx = int(input("Enter number: ")) - 1
                if 0 <= idx < len(potential_dirs):
                    selection = potential_dirs[idx]
                else:
                    print("Invalid selection. Try again.")
            except ValueError:
                print("Please enter a number.")
                
        print(f"Using content directory: {selection}")
        return selection
    
    def _setup_chromadb(self):
        """Set up the ChromaDB connection"""
        if self.use_chroma:
            # Use persistent client with path to the chroma_db directory
            chroma_dir = os.path.join(self.content_dir, "chroma_db")
            
            if not os.path.exists(chroma_dir):
                raise FileNotFoundError(
                    f"ChromaDB directory not found at {chroma_dir}. "
                    "Please run retrieval.py first to create the vector database."
                )
                
            # Initialize persistent client
            self.chroma_client = chromadb.PersistentClient(path=chroma_dir)
            sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Create or get collection
            collection_name = f"pdf_chunks_{os.path.basename(self.content_dir)}"
            try:
                self.collection = self.chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=sentence_transformer_ef
                )
                print(f"Connected to existing persistent ChromaDB collection: {collection_name}")
            except Exception as e:
                raise ValueError(
                    f"ChromaDB collection '{collection_name}' not found or could not be accessed. "
                    f"Error: {str(e)}. "
                    "Please run retrieval.py first to create the collection."
                )
    
    def load_chunks(self):
        """Load the chunks from the JSON file"""
        chunks_path = os.path.join(self.content_dir, "rag_chunks.json")
        
        if not os.path.exists(chunks_path):
            raise FileNotFoundError(f"Chunks file not found at {chunks_path}")
            
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
            
        print(f"Loaded {len(self.chunks)} chunks from {chunks_path}")
    
    def retrieve_context(self, query, top_k=3):
        """
        Retrieve relevant context based on the query
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
            
        Returns:
            List of context chunks
        """
        if self.use_chroma:
            # Use ChromaDB for search
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # Format results to match the original format
            contexts = []
            for i, doc_id in enumerate(results["ids"][0]):
                # Find original chunk
                for chunk in self.chunks:
                    if str(chunk["id"]) == doc_id:
                        contexts.append({
                            "text": chunk["text"],
                            "section_title": chunk["section_title"],
                            "start_page": chunk["start_page"],
                            "score": float(results["distances"][0][i]) if "distances" in results else 0.0
                        })
                        break
            
            return contexts
        else:
            raise ValueError("ChromaDB is required for context retrieval")
    
    def format_context_for_prompt(self, contexts):
        """Format retrieved contexts for the prompt"""
        context_text = ""
        
        for i, ctx in enumerate(contexts):
            context_text += f"[Context {i+1} - Page {ctx.get('start_page', 'unknown')} - {ctx.get('section_title', 'Section')}]\n"
            context_text += f"{ctx['text']}\n\n"
            
        return context_text.strip()
    
    def get_response(self, query, top_k=3):
        """
        Get response from Gemini with relevant context
        
        Args:
            query: User query
            top_k: Number of context chunks to use
            
        Returns:
            Generated response
        """
        # Retrieve relevant context
        contexts = self.retrieve_context(query, top_k=top_k)
        
        if not contexts:
            system_prompt = "You are a helpful assistant. If you don't know the answer, say you don't know."
            context_text = "No relevant context found in the document."
        else:
            system_prompt = (
                "You are a helpful assistant specialized in answering questions based on the provided document context. "
                "Use only information from the provided context to answer the user's question. "
                "If the context doesn't contain enough information to answer, say you don't have enough information. "
                "Always cite the page numbers from the context you used."
            )
            context_text = self.format_context_for_prompt(contexts)
            
        # Create the full prompt
        full_prompt = f"{system_prompt}\n\nDocument Context:\n{context_text}\n\nUser Question: {query}\n\nAssistant:"
        
        # Get response from Gemini using the client approach
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def chat(self):
        """Interactive chat interface"""
        print("\n" + "="*60)
        print("PDF Chatbot ready! Ask questions about your document.")
        print("Type 'exit', 'quit', or 'q' to end the conversation.")
        print("="*60 + "\n")
        
        while True:
            user_query = input("\nYou: ")
            
            if user_query.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye!")
                break
                
            if not user_query.strip():
                continue
                
            print("\nThinking...")
            response = self.get_response(user_query)
            
            print(f"\nAssistant: {response}")
            
            # Add to history
            self.chat_history.append({"user": user_query, "assistant": response})

def main():
    """Main function to run the chatbot"""
    parser = argparse.ArgumentParser(description="Chat with your PDF documents using Gemini")
    parser.add_argument("--content_dir", "-d", help="Directory containing the extracted content")
    parser.add_argument("--model", "-m", default="gemini-2.0-flash", help="Gemini model to use")
    parser.add_argument("--top_k", "-k", type=int, default=3, help="Number of context chunks to use")
    args = parser.parse_args()
    
    try:
        # Initialize and start chatbot
        chatbot = PdfChatbot(
            content_dir=args.content_dir,
            model_name=args.model
        )
        chatbot.chat()
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo use this chatbot:")
        print("1. First run pre.py to extract content from your PDF")
        print("2. Then run retrieval.py to create the vector database")
        print("3. Make sure you have a GEMINI_API_KEY in your environment or .env file")
        print("4. Try again!")

if __name__ == "__main__":
    main()
