import numpy as np
import cv2
import os
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import re
import json
from similarity_img import rank_similar_images

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API with the key from environment variables
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

def setup_chromadb(content_dir):
    """
    Set up the ChromaDB connection
    
    Args:
        content_dir: Directory containing extracted content and ChromaDB
        
    Returns:
        tuple: (collection, sentence_transformer_model)
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
    except Exception as e:
        raise ValueError(
            f"ChromaDB collection '{collection_name}' not found or could not be accessed. "
            f"Error: {str(e)}. "
            "Please run retrieval.py first to create the collection."
        )
    
    return collection, sentence_transformer_model

def crop_image(image, box):
    """
    Crops an image according to the box coordinates
    
    Args:
        image: The input image as a numpy array
        box: Box coordinates [x0, y0, x1, y1]
        
    Returns:
        Cropped image as numpy array
    """
    x0, y0, x1, y1 = box[0]
    
    height, width = image.shape[:2]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(width, x1)
    y1 = min(height, y1)
    
    cropped_image = image[y0:y1, x0:x1]
    return cropped_image

def expand_query(model, query):
    """
    Expand the query with synonyms and related terms
    
    Args:
        model: The generative model to use
        query: The original query text
        
    Returns:
        Expanded query with additional relevant terms
    """
    try:
        expansion_prompt = f"""
        I need to expand this search query to improve retrieval results: "{query}"
        
        Please generate:
        1. 2-3 synonymous ways to phrase the same query
        2. 3-4 related keywords that could help in document retrieval
        3. Any potentially disambiguating terms if the query is unclear
        
        Format the output as a single line with all terms separated by spaces.
        Only include relevant terms, no explanations or other text.
        """
        
        response = model.generate_content(expansion_prompt)
        expanded_terms = response.text.strip()
        expanded_query = f"{query} {expanded_terms}"
        return expanded_query
        
    except Exception:
        return query

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
    query_terms = set(query.lower().split())
    
    for chunk in chunks:
        chunk_text = chunk.get('text', '').lower()
        matched_terms = sum(1 for term in query_terms if term in chunk_text)
        
        score = matched_terms
        
        section_title = chunk.get('section_title', '').lower()
        section_match = sum(1 for term in query_terms if term in section_title)
        score += section_match * 2
        
        chunk['score'] = score
    
    ranked_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)
    return ranked_chunks[:top_k]

def get_image_description(image_path, box_coordinates, model_text=None, text_col=None, chunks=None):
    """
    Gets image description and key terms for an image region
    
    Args:
        image_path: Path to the image
        box_coordinates: Box coordinates [x0, y0, x1, y1]
        model_text: Optional text model
        text_col: Optional text collection
        chunks: Optional chunks data
        
    Returns:
        Dictionary with description and key terms
    """
    image = cv2.imread(image_path)
    if image is None:
        return "Error: Could not load image"
    
    if not isinstance(box_coordinates, np.ndarray):
        box_coordinates = np.array([box_coordinates], dtype=np.int32)
    
    crop = crop_image(image, box_coordinates)
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        crop_pil = Image.fromarray(crop)

        description_prompt = "Describe briefly and technically what component of the CUPRA Tavascan dashboard is shown in this image. Be specific and use technical terms. Don't explain the component, just describe it. " + str(crop_pil)
        description_response = model.generate_content([description_prompt, crop_pil])
        image_description = description_response.text.strip()
        
        keywords_prompt = "Extract exactly 3-5 technical key terms from this text that appear in the official CUPRA Tavascan manual. Return ONLY the terms as a comma-separated list with NO introductory text, NO numbering, and NO bullet points: " + image_description
        keywords_response = model.generate_content(keywords_prompt)
        raw_keywords = keywords_response.text.strip()
        
        cleaned_keywords = raw_keywords
        
        prefixes_to_remove = [
            "Here are", "These are", "The technical", "Technical key", 
            "Key terms", "Terms:", "1.", "•", "-", "*"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned_keywords.startswith(prefix):
                cleaned_keywords = cleaned_keywords[len(prefix):].strip()
        
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
        
        return {
            "description": image_description,
            "key_terms": cleaned_keywords
        }
        
    except Exception as e:
        return f"Error processing image with Gemini API: {str(e)}\n\nTip: Make sure GOOGLE_API_KEY is correctly set in your .env file."

def retrieve_context(query, top_k=15, collection=None, chunks=None, content_dir=None):
    """
    Retrieve relevant context based on the query and return a list of image paths
    
    Args:
        query: The search query
        top_k: Number of results to retrieve
        collection: ChromaDB collection
        chunks: Content chunks
        content_dir: Directory containing content
        
    Returns:
        Tuple of (image_paths, image_contexts)
    """
    if collection and chunks:
        results = collection.query(
            query_texts=[query],
            n_results=top_k * 2
        )
        
        contexts = []
        for i, doc_id in enumerate(results["ids"][0]):
            for chunk in chunks:
                if str(chunk["id"]) == doc_id:
                    contexts.append({
                        "text": chunk["text"],
                        "section_title": chunk["section_title"],
                        "start_page": chunk["start_page"],
                        "score": float(results["distances"][0][i]) if "distances" in results else 0.0
                    })
                    break

        top_pages = [ctx["start_page"] for ctx in contexts[:top_k]]

        extracted_content_path = os.path.join(content_dir, "extracted_content.json")
        if not os.path.exists(extracted_content_path):
            raise FileNotFoundError(f"File not found: {extracted_content_path}")

        with open(extracted_content_path, "r", encoding="utf-8") as f:
            extracted_content = json.load(f)

        image_paths = [
            image["path"] for chunk in extracted_content
            if chunk.get("page_num") in top_pages and "images" in chunk
            for image in chunk["images"]
        ]
        image_contexts = {
            image["path"]: (chunk.get("page_num"), image["nearby_text"])
            for chunk in extracted_content
            if chunk.get("page_num") in top_pages and "images" in chunk
            for image in chunk["images"]
        }

        return image_paths, image_contexts
    
    return [], {}

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
        
        for i, ctx in enumerate(reranked_chunks):
            context_text += f"[Context {i+1} - Page {ctx.get('start_page', 'unknown')} - {ctx.get('section_title', 'Section')}]\n"
            context_text += f"{ctx['text']}\n\n"
        
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
            
            response_clean = re.sub(r'```json', '', response_text)
            response_clean = re.sub(r'```', '', response_clean)
            
            try:
                response_json = json.loads(response_clean)
                self.chat_history.append({"user": query, "assistant": response_json})
                return response_json
            except json.JSONDecodeError:
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

def process_dashboard_component(image_path, box_coordinates, content_dir=None):
    """
    Main function to process a dashboard component and return a JSON response
    
    Args:
        image_path: Path to the image file
        box_coordinates: List of coordinates [x0, y0, x1, y1]
        content_dir: Directory containing extracted content and ChromaDB (optional)
        
    Returns:
        JSON response with component description and relevant information
    """
    if not api_key:
        return {
            "error": "GEMINI_API_KEY not found in .env file",
            "message": "Please create an .env file with your Gemini API key: GEMINI_API_KEY=your_api_key_here"
        }
    
    # Convert box_coordinates to numpy array if not already
    if not isinstance(box_coordinates, np.ndarray):
        box_coordinates = np.array([box_coordinates], dtype=np.int32)
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return {"error": f"Could not load image from path: {image_path}"}
    
    # Default content directory if not provided
    if content_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        content_dir = os.path.join(script_dir, "..", "extracted_content_manual")
    
    try:
        # Setup ChromaDB
        text_col, model_text = setup_chromadb(content_dir)
        
        # Load chunks for retrieval
        chunks_path = os.path.join(content_dir, "rag_chunks.json")
        if os.path.exists(chunks_path):
            with open(chunks_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
        else:
            chunks = None
            return {"error": "rag_chunks.json not found. Please run extraction process first."}
        
        # Crop the image
        cropped = crop_image(image, box_coordinates)
        
        # Get image description
        description = get_image_description(image_path, box_coordinates)
        
        # Retrieve context
        image_paths_list, image_contexts = retrieve_context(
            query=description["description"],
            top_k=20,
            collection=text_col,
            chunks=chunks,
            content_dir=content_dir
        )

        # Rank similar images
        scores = rank_similar_images(cropped, top_k=3, image_paths_list=image_paths_list)
        
        # Extract page numbers from image contexts
        top_pages = list(set([image_contexts[img[0]][0] for img in scores if img[0] in image_contexts]))

        # Collect all chunks from the top pages
        all_chunks_from_pages = [
            chunk for chunk in chunks if chunk["start_page"] in top_pages
        ]

        # Re-rank the chunks based on the query
        reranked_chunks = _rerank_chunks(all_chunks_from_pages, description["description"], top_k=3)

        # Generate response
        chat_session = ImageChatSession()
        json_response = chat_session.generate_json_response(
            description["description"], 
            reranked_chunks, 
            image_contexts, 
            scores
        )

        return json_response
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to process dashboard component"
        }

# Command-line interface functionality
def main():
    # Example usage when run as script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "..", "..", "cupra_frames", "1.png")
    content_dir = os.path.join(script_dir, "..", "extracted_content_manual")
    
    box = np.array([[497, 245, 700, 351]], dtype=np.int32)
    
    result = process_dashboard_component(image_path, box, content_dir)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()


