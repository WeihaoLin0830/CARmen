import numpy as np
import cv2
import os
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import re  # Added for regex pattern matching
import json  # Added for JSON handling
from similarity_img import rank_similar_images  # Import the ranking function from similarity_img.py

class DashboardImageProcessor:
    """Class to handle processing dashboard images with Gemini API and ChromaDB"""
    
    def __init__(self, model_name="gemini-2.0-flash-001"):
        """
        Initialize the processor with API keys and models
        
        Args:
            model_name: The Gemini model to use
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Configure Gemini API with the key from environment variables
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        self.model_name = model_name
        self.model = None
        self.text_col = None
        self.model_text = None
        self.chunks = None
    
    def setup_chromadb(self, content_dir):
        """Set up the ChromaDB connection
        
        Args:
            content_dir: Directory where the ChromaDB is stored
            
        Returns:
            Tuple containing (collection, sentence_transformer_model)
        """
        # Use persistent client with path to the chroma_db directory
        chroma_dir = os.path.join(content_dir, "chroma_db")
        
        if not os.path.exists(chroma_dir):
            raise FileNotFoundError(
                f"ChromaDB directory not found at {chroma_dir}. "
                "Please run retrieval.py first to create the vector database."
            )
                
        # Initialize persistent client
        chroma_client = chromadb.PersistentClient(path=chroma_dir)
        
        # Initialize the sentence transformer model
        sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Create or get collection
        collection_name = f"pdf_chunks_{os.path.basename(content_dir)}"
        try:
            collection = chroma_client.get_collection(
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
        
        self.text_col = collection
        self.model_text = sentence_transformer_model
        return collection, sentence_transformer_model

    def load_chunks(self, content_dir):
        """Load the RAG chunks from the content directory
        
        Args:
            content_dir: Directory with extracted content
            
        Returns:
            List of chunks if successful, None otherwise
        """
        chunks_path = os.path.join(content_dir, "rag_chunks.json")
        if os.path.exists(chunks_path):
            with open(chunks_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            print(f"Loaded {len(self.chunks)} chunks for retrieval")
            return self.chunks
        else:
            print("Warning: rag_chunks.json not found. Advanced retrieval functionality will be limited.")
            return None

    def crop_image(self, image, box):
        """
        Crops an image according to the coordinates of a box.
        
        Args:
            image: Input image (numpy array)
            box: Numpy array with coordinates [x0, y0, x1, y1]
        
        Returns:
            Cropped image
        """
        # Extract coordinates
        x0, y0, x1, y1 = box[0]
        
        # Ensure coordinates are within image boundaries
        height, width = image.shape[:2]
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(width, x1)
        y1 = min(height, y1)
        
        # Crop the image
        cropped_image = image[y0:y1, x0:x1]
        
        return cropped_image

    def expand_query(self, query):
        """
        Expand the query with synonyms and related terms
        
        Args:
            query: The original query
            
        Returns:
            Expanded query with additional related terms
        """
        try:
            if not self.model:
                self.model = genai.GenerativeModel(self.model_name)
                
            # Use a separate generation model for query expansion
            expansion_prompt = f"""
            I need to expand this search query to improve retrieval results: "{query}"
            
            Please generate:
            1. 2-3 synonymous ways to phrase the same query
            2. 3-4 related keywords that could help in document retrieval
            3. Any potentially disambiguating terms if the query is unclear
            
            Format the output as a single line with all terms separated by spaces.
            Only include relevant terms, no explanations or other text.
            """
            
            # Generate expanded terms
            response = self.model.generate_content(expansion_prompt)
            expanded_terms = response.text.strip()
            
            # Combine original query with expanded terms
            expanded_query = f"{query} {expanded_terms}"
            
            print(f"Original query: {query}")
            print(f"Expanded query: {expanded_query}")
            
            return expanded_query
            
        except Exception as e:
            print(f"Query expansion error: {str(e)}")
            # Fall back to original query if expansion fails
            return query

    # Add the other methods following the same pattern...
    
    def get_image_description(self, image_path, box_coordinates):
        """
        Loads an image, crops it according to the given coordinates, and gets key terms
        related to the component shown.
        
        Args:
            image_path: Path to the image file
            box_coordinates: Array with coordinates [x0, y0, x1, y1]
            
        Returns:
            Key terms extracted from the image
        """
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            return "Error: Could not load image"
        
        # Convert coordinates to expected format
        if not isinstance(box_coordinates, np.ndarray):
            box_coordinates = np.array([box_coordinates], dtype=np.int32)
        
        # Crop the image
        crop = self.crop_image(image, box_coordinates)
        
        try:
            # Initialize the model if not already done
            if not self.model:
                self.model = genai.GenerativeModel(self.model_name)
                
            # Convert to PIL Image
            crop_pil = Image.fromarray(crop)

            # Request a detailed description of the selected region
            description_prompt = "Describe briefly and technically what component of the CUPRA Tavascan dashboard is shown in this image. Be specific and use technical terms. Don't explain the component, just describe it. " + str(crop_pil)
            description_response = self.model.generate_content([description_prompt, crop_pil])
            image_description = description_response.text.strip()
            
            print(f"Generated description: {image_description}")
            
            # Extract keywords only
            keywords_prompt = "Extract exactly 3-5 technical key terms from this text that appear in the official CUPRA Tavascan manual. Return ONLY the terms as a comma-separated list with NO introductory text, NO numbering, and NO bullet points: " + image_description
            keywords_response = self.model.generate_content(keywords_prompt)
            raw_keywords = keywords_response.text.strip()
            
            # Clean up any remaining introductory text or formatting
            cleaned_keywords = raw_keywords
            
            # Remove common prefixes
            prefixes_to_remove = [
                "Here are", "These are", "The technical", "Technical key", 
                "Key terms", "Terms:", "1.", "•", "-", "*"
            ]
            
            for prefix in prefixes_to_remove:
                if cleaned_keywords.startswith(prefix):
                    cleaned_keywords = cleaned_keywords[len(prefix):].strip()
            
            # Remove phrases like "technical terms:" or "extracted from the text:"
            intro_phrases = [
                "technical key terms", "key terms", "terms extracted", 
                "extracted from", "from the text", "that appear", "would appear"
            ]
            
            for phrase in intro_phrases:
                if phrase in cleaned_keywords.lower():
                    phrase_index = cleaned_keywords.lower().find(phrase)
                    colon_index = cleaned_keywords.find(":", phrase_index)
                    if colon_index != -1:
                        cleaned_keywords = cleaned_keywords[colon_index+1:].strip()
            
            print(f"Extracted keywords: {cleaned_keywords}")
            
            # Return only the keywords
            return {
                "description": image_description,
                "key_terms": cleaned_keywords
            }
            
        except Exception as e:
            return f"Error processing image with Gemini API: {str(e)}\n\nTip: Make sure GOOGLE_API_KEY is correctly set in your .env file."

def _rerank_chunks(chunks, query, top_k=3):
    """
    Re-rank chunks based on relevance to the query
    
    Args:
        chunks: List of chunks to re-rank
        query: User query
        top_k: Number of chunks to return
        
    Returns:
        List of most relevant chunks
    """
    # Calculate relevance scores using simple term matching
    query_terms = set(query.lower().split())
    
    for chunk in chunks:
        # Count term overlap between query and chunk text
        chunk_text = chunk.get('text', '').lower()
        matched_terms = sum(1 for term in query_terms if term in chunk_text)
        
        # Simple scoring: term frequency + section title match bonus
        score = matched_terms
        
        # Add bonus for section title matches
        section_title = chunk.get('section_title', '').lower()
        section_match = sum(1 for term in query_terms if term in section_title)
        score += section_match * 2  # Title matches get double weight
        
        # Store score in chunk
        chunk['score'] = score
    
    # Sort by score (descending) and return top_k
    ranked_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)
    return ranked_chunks[:top_k]

def retrieve_context(query, top_k=15, collection=None, chunks=None):
    """
    Retrieve relevant context based on the query and return a list of image paths
    
    Args:
        query: User query
        top_k: Number of chunks to retrieve
        collection: ChromaDB collection for retrieval
        chunks: List of document chunks
        
    Returns:
        List of paths to images found in the relevant pages
    """
    if collection and chunks:
        # Use ChromaDB for search with the original query
        results = collection.query(
            query_texts=[query],
            n_results=top_k * 2  # Retrieve more results initially as we'll filter them later
        )
        
        # Format results to match the original format
        contexts = []
        for i, doc_id in enumerate(results["ids"][0]):
            # Find original chunk
            for chunk in chunks:
                if str(chunk["id"]) == doc_id:
                    contexts.append({
                        "text": chunk["text"],
                        "section_title": chunk["section_title"],
                        "start_page": chunk["start_page"],
                        "score": float(results["distances"][0][i]) if "distances" in results else 0.0
                    })
                    break

        # Extract the start pages of the top chunks
        top_pages = [ctx["start_page"] for ctx in contexts[:top_k]]

        # Load extracted content JSON
        extracted_content_path = os.path.join(content_dir, "extracted_content.json")
        if not os.path.exists(extracted_content_path):
            raise FileNotFoundError(f"File not found: {extracted_content_path}")

        with open(extracted_content_path, "r", encoding="utf-8") as f:
            extracted_content = json.load(f)

        # Filter image paths that match the top pages
        image_paths = [
            image["path"] for chunk in extracted_content
            if chunk.get("page_num") in top_pages and "images" in chunk
            for image in chunk["images"]
        ]
        # Create a dictionary linking image paths with a tuple of page number and nearby text
        image_contexts = {
            image["path"]: (chunk.get("page_num"), image["nearby_text"])
            for chunk in extracted_content
            if chunk.get("page_num") in top_pages and "images" in chunk
            for image in chunk["images"]
        }

        return image_paths, image_contexts  # Return the list of image paths
    
    return [], {}  # Return empty lists if conditions not met

class ImageChatSession:
    """Chat session class for interacting with the model using image context"""
    def __init__(self, model_name="gemini-2.0-flash-001"):
        """Initialize a chat session with Gemini"""
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.chat_history = []
        
    def format_context_for_prompt(self, reranked_chunks, image_contexts, similar_images):
        """Format the context from chunks and images into a prompt"""
        context_text = "Document Context:\n\n"
        
        # Add text chunks context
        for i, ctx in enumerate(reranked_chunks):
            context_text += f"[Context {i+1} - Page {ctx.get('start_page', 'unknown')} - {ctx.get('section_title', 'Section')}]\n"
            context_text += f"{ctx['text']}\n\n"
        
        # Add image context
        context_text += "Relevant Images:\n\n"
        for i, (img_path, score) in enumerate(similar_images):
            page_num, nearby_text = image_contexts.get(img_path, (None, "No nearby text"))
            context_text += f"[Image {i+1} - Page {page_num}]\n"
            context_text += f"Description: {nearby_text}\n\n"
            
        return context_text
    
    def generate_json_response(self, query, reranked_chunks, image_contexts, similar_images):
        """Generate a JSON formatted response based on the context provided"""
        context_text = self.format_context_for_prompt(reranked_chunks, image_contexts, similar_images)
        
        json_prompt = f"""
        Based on the following document context about the CUPRA Tavascan dashboard:

        {context_text}

        Answer this user question: "{query}"
        
        Format your response as a valid JSON object with these fields:
        - "answer": Provide an expert yet conversational description of this CUPRA Tavascan component. Cover its name, function, how it enhances the driving experience, and any unique features that distinguish it. Draw on the context provided to deliver accurate technical information in an engaging way. Do it very concisely and don't mention that you have used provided context.
        - "page_numbers": An array of page numbers that contain relevant information
        - "figure_numbers": An array of figure references if any are mentioned in the context
        
        Return ONLY the JSON object without any other text or code formatting.
        """
        
        try:
            response = self.model.generate_content(json_prompt)
            response_text = response.text.strip()
            
            # Clean up the response to get valid JSON
            response_clean = re.sub(r'```json', '', response_text)
            response_clean = re.sub(r'```', '', response_clean)
            
            # Try to parse as JSON
            try:
                response_json = json.loads(response_clean)
                self.chat_history.append({"user": query, "assistant": response_json})
                return response_json
            except json.JSONDecodeError:
                # Fallback if parsing fails
                fallback_response = {
                    "answer": response_text,
                    "page_numbers": [ctx.get('start_page') for ctx in reranked_chunks if 'start_page' in ctx],
                    "figure_numbers": []
                }
                self.chat_history.append({"user": query, "assistant": fallback_response})
                return fallback_response
                
        except Exception as e:
            error_response = {
                "answer": f"Error generating response: {str(e)}",
                "page_numbers": [],
                "figure_numbers": []
            }
            self.chat_history.append({"user": query, "assistant": error_response})
            return error_response

# Si se ejecuta como script principal
if __name__ == "__main__":
    # Obtener la ruta del script actual
    api_key = os.getenv('GEMINI_API_KEY')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construir la ruta relativa desde el script
    image_path = os.path.join(script_dir, "..", "..", "cupra_frames", "1.png")
    # Ruta correcta al directorio que contiene la colección ChromaDB
    content_dir = os.path.join(script_dir, "..", "extracted_content_manual")
    
    image = cv2.imread(image_path)
    box = np.array([[497, 245, 700, 351]], dtype=np.int32)

    # Verificar que la API key está configurada
    if not api_key:
        print("ERROR: GEMINI_API_KEY no encontrada en el archivo .env")
        print("Por favor, crea un archivo .env con tu API key de Gemini:")
        print("GEMINI_API_KEY=your_api_key_here")
        exit(1)
    
    # Setup ChromaDB with the correct path
    try:
        processor = DashboardImageProcessor()
        text_col, model_text = processor.setup_chromadb(content_dir)
        print("ChromaDB setup successful. Using full RAG capabilities.")
        
        # Load chunks for advanced retrieval functionality
        chunks = processor.load_chunks(content_dir)
        
        # Ejemplo de uso del recorte simple
        cropped = processor.crop_image(image, box)
        
        # Uso completo con RAG
        description = processor.get_image_description(image_path, box)
        
        print("\n")

        # Pass the collection and chunks to the retrieve_context function
        image_paths_list, image_contexts = retrieve_context(
            query=description["description"],
            top_k=20,
            collection=text_col,
            chunks=chunks
        )

        scores = rank_similar_images(cropped, top_k=3, image_paths_list=image_paths_list)
        print(f"Ranked similar images: {scores}")

        context_near = []
        for i in scores:
            if i[0] in image_contexts:
                page_num, nearby_text = image_contexts[i[0]]
                context_near.append({"page_num": page_num, "nearby_text": nearby_text})

        # Extract page numbers from image contexts
        top_pages = list(set([image_contexts[img[0]][0] for img in scores if img[0] in image_contexts]))

        # Collect all chunks from the top pages
        all_chunks_from_pages = [
            chunk for chunk in chunks if chunk["start_page"] in top_pages
        ]

        # Re-rank the chunks based on the query
        reranked_chunks = _rerank_chunks(all_chunks_from_pages, description["description"], top_k=3)

        print("\nRe-ranked chunks:")
        print(reranked_chunks)

        # Initialize chat session and generate JSON response
        chat_session = ImageChatSession()
        json_response = chat_session.generate_json_response(
            description["description"], 
            reranked_chunks, 
            image_contexts, 
            scores
        )

        print("\nJSON formatted answer:")
        print(json.dumps(json_response, indent=2))

        # Prompt user if they want to ask follow-up questions
        print("\nDo you want to ask follow-up questions about this dashboard component? (y/n)")
        user_choice = input().strip().lower()
        
        if user_choice == 'y':
            while True:
                user_query = input("\nEnter your question (or 'exit' to quit): ")
                if user_query.lower() in ['exit', 'quit', 'q']:
                    break
                    
                json_response = chat_session.generate_json_response(
                    user_query, 
                    reranked_chunks, 
                    image_contexts, 
                    scores
                )
                
                print("\nJSON formatted answer:")
                print(json.dumps(json_response, indent=2))
        
        print("Basic retrieval results:")
        print(image_paths_list)
        
    except Exception as e:
        print(f"ChromaDB setup failed: {e}")
        print("Falling back to basic image description (no RAG).")
        
        # Ejemplo de uso del recorte simple
        cropped = processor.crop_image(image, box)
        
        # Uso básico sin RAG
        description = processor.get_image_description(image_path, box)


