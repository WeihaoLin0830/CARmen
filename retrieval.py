import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import argparse
from tqdm import tqdm
import re
import chromadb
from chromadb.utils import embedding_functions

class DocumentRetrieval:
    def __init__(self, content_dir=None, model_name="all-MiniLM-L6-v2", use_chroma=True):
        """
        Initialize the retrieval system with extracted content
        
        Args:
            content_dir: Directory containing the extracted content
            model_name: Name of the embedding model to use
            use_chroma: Whether to use ChromaDB for vector storage
        """
        self.content_dir = self._find_content_dir(content_dir)
        self.chunks = []
        self.use_chroma = use_chroma
        
        # Setup embeddings model
        self.model = SentenceTransformer(model_name)
        
        # Setup ChromaDB if enabled
        if use_chroma:
            # Create persistent storage directory within content directory
            chroma_dir = os.path.join(self.content_dir, "chroma_db")
            if not os.path.exists(chroma_dir):
                os.makedirs(chroma_dir)
                
            # Initialize persistent client
            self.chroma_client = chromadb.PersistentClient(path=chroma_dir)
            sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
            
            # Create or get collection
            collection_name = f"pdf_chunks_{os.path.basename(self.content_dir)}"
            try:
                self.collection = self.chroma_client.get_collection(
                    name=collection_name, 
                    embedding_function=sentence_transformer_ef
                )
                print(f"Using existing persistent ChromaDB collection: {collection_name}")
            except:
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=sentence_transformer_ef
                )
                print(f"Created new persistent ChromaDB collection: {collection_name}")
        
        # Load the chunks
        self.load_chunks()
        
        print(f"Retrieval system initialized with {len(self.chunks)} chunks")
    
    def _find_content_dir(self, content_dir=None):
        """Find content directory if not specified"""
        if content_dir and os.path.exists(content_dir):
            return content_dir
            
        # Look for directories that match the pattern "extracted_content_*"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        potential_dirs = []
        
        for item in os.listdir(current_dir):
            if os.path.isdir(item) and item.startswith("extracted_content_"):
                potential_dirs.append(item)
                
        if not potential_dirs:
            raise FileNotFoundError("No extracted content directories found. Please process a PDF first.")
            
        if len(potential_dirs) == 1:
            print(f"Using content directory: {potential_dirs[0]}")
            return potential_dirs[0]
            
        # If multiple directories, ask the user to select one
        print("Multiple content directories found. Please select one:")
        for i, directory in enumerate(potential_dirs):
            print(f"[{i+1}] {directory}")
            
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
        
    def load_chunks(self):
        """Load the RAG chunks from the output directory"""
        chunks_path = os.path.join(self.content_dir, "rag_chunks.json")
        
        if not os.path.exists(chunks_path):
            raise FileNotFoundError(f"Chunks file not found at {chunks_path}")
            
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
            
        print(f"Loaded {len(self.chunks)} chunks from {chunks_path}")
        
        # If using ChromaDB, add chunks to collection if not already there
        if self.use_chroma:
            # Check how many documents are in the collection
            collection_count = self.collection.count()
            
            if collection_count < len(self.chunks):
                print(f"Adding {len(self.chunks) - collection_count} chunks to ChromaDB...")
                
                # Prepare data for bulk insertion
                ids = []
                texts = []
                metadatas = []
                
                for i, chunk in enumerate(self.chunks):
                    if i < collection_count:
                        continue
                        
                    chunk_id = str(chunk["id"])
                    ids.append(chunk_id)
                    texts.append(chunk["text"])
                    
                    # Store metadata (everything except the text field)
                    metadata = {k: str(v) if not isinstance(v, (int, float, bool, str)) else v 
                               for k, v in chunk.items() if k != "text"}
                    metadatas.append(metadata)
                
                # Add to collection in batches to prevent memory issues
                batch_size = 100
                for i in range(0, len(ids), batch_size):
                    end_idx = min(i + batch_size, len(ids))
                    self.collection.add(
                        ids=ids[i:end_idx],
                        documents=texts[i:end_idx],
                        metadatas=metadatas[i:end_idx]
                    )
                    
                print(f"Added chunks to ChromaDB collection")
    
    def search(self, query, top_k=3):
        """
        Search for relevant chunks based on the query
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of relevant chunks
        """
        if self.use_chroma:
            # Use ChromaDB for search
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # Format results to match the original format
            formatted_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                # Find original chunk
                for chunk in self.chunks:
                    if str(chunk["id"]) == doc_id:
                        result = chunk.copy()
                        result["score"] = float(results["distances"][0][i]) if "distances" in results else 0.0
                        formatted_results.append(result)
                        break
            
            return formatted_results
        else:
            # Use original in-memory search approach
            # Generate embedding for the query
            query_embedding = self.model.encode([query])[0]
            
            # Calculate cosine similarity
            scores = np.dot(self.embeddings, query_embedding) / (
                np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            
            # Get top_k results
            top_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            
            for idx in top_indices:
                result = self.chunks[idx].copy()
                result["score"] = float(scores[idx])
                results.append(result)
                
            return results
    
    def display_results(self, results):
        """Format and display search results"""
        if not results:
            print("\nNo matching results found.")
            return
            
        print("\n" + "="*50)
        print("SEARCH RESULTS:")
        print("="*50)
        
        for i, result in enumerate(results):
            print(f"\n[{i+1}] Score: {result.get('score', 0):.4f}")
            print(f"Title: {result['section_title']}")
            print(f"Page: {result['start_page']}")
            print("-"*50)
            
            # Display a snippet of the text
            max_snippet_len = 300
            text = result["text"]
            if len(text) > max_snippet_len:
                text = text[:max_snippet_len] + "..."
            print(text)
            
            # Show if there are images
            if result["images"]:
                print(f"\nContains {len(result['images'])} images")
                
            print("-"*50)
    
    def get_image_paths(self, result):
        """Get full paths to images in a result"""
        image_paths = []
        for img in result.get("images", []):
            if "path" in img:
                # Convert relative path to absolute path
                image_path = os.path.join(self.content_dir, "images", os.path.basename(img["path"]))
                if os.path.exists(image_path):
                    image_paths.append(image_path)
        return image_paths

def main():
    """Main function to run the retrieval system"""
    parser = argparse.ArgumentParser(description="Retrieve information from processed PDF content")
    parser.add_argument("--content_dir", "-d", help="Directory containing the extracted content")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--top_k", "-k", type=int, default=3, help="Number of results to return")
    parser.add_argument("--no-chroma", action="store_true", help="Don't use ChromaDB")
    args = parser.parse_args()
    
    # Initialize the retrieval system
    try:
        retrieval = DocumentRetrieval(
            content_dir=args.content_dir, 
            use_chroma=not args.no_chroma
        )
        
        # Interactive mode if no query provided
        if not args.query:
            print("\nEnter your queries (type 'exit' to quit):")
            while True:
                query = input("\nQuery: ")
                if query.lower() in ["exit", "quit", "q"]:
                    break
                    
                if not query.strip():
                    continue
                    
                results = retrieval.search(query, top_k=args.top_k)
                retrieval.display_results(results)
        else:
            # Single query mode
            results = retrieval.search(args.query, top_k=args.top_k)
            retrieval.display_results(results)
    
    except Exception as e:
        print(f"Error: {e}")
        print("If you haven't processed any PDFs yet, run pre.py first.")

if __name__ == "__main__":
    main()
