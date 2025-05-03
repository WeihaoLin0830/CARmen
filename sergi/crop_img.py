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
from similarity_img import rank_similar_images  # Import the ranking function from similarity_img.py

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API with the key from environment variables
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

def setup_chromadb(content_dir):
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
    
    return collection, sentence_transformer_model

def crop_image(image, box):
    """
    Recorta una imagen según las coordenadas de una caja.
    
    Args:
        image: Imagen de entrada (numpy array)
        box: Array numpy con las coordenadas [x0, y0, x1, y1]
    
    Returns:
        Imagen recortada
    """
    # Extraer coordenadas
    x0, y0, x1, y1 = box[0]
    
    # Asegurar que las coordenadas estén dentro de los límites de la imagen
    height, width = image.shape[:2]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(width, x1)
    y1 = min(height, y1)
    
    # Recortar la imagen
    cropped_image = image[y0:y1, x0:x1]
    
    return cropped_image

def expand_query(model, query):
    """
    Expand the query with synonyms and related terms
    
    Args:
        model: The generative model to use for expansion
        query: The original query
        
    Returns:
        Expanded query with additional related terms
    """
    try:
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
        response = model.generate_content(expansion_prompt)
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

def get_image_description(image_path, box_coordinates, model_text=None, text_col=None, chunks=None):
    """
    Carga una imagen, la recorta según las coordenadas dadas y obtiene los términos clave
    relacionados con el componente mostrado.
    
    Args:
        image_path: Ruta al archivo de imagen
        box_coordinates: Array con coordenadas [x0, y0, x1, y1]
        model_text: Modelo de embeddings de texto (opcional)
        text_col: Colección para consulta de texto (opcional)
        chunks: Lista de chunks de texto del documento (opcional)
        
    Returns:
        Términos clave extraídos de la imagen
    """
    # Cargar la imagen
    image = cv2.imread(image_path)
    if image is None:
        return "Error: No se pudo cargar la imagen"
    
    # Convertir las coordenadas al formato esperado
    if not isinstance(box_coordinates, np.ndarray):
        box_coordinates = np.array([box_coordinates], dtype=np.int32)
    
    # Recortar la imagen
    crop = crop_image(image, box_coordinates)
    
    try:
        # --- Generar descripción y extraer términos clave ---
        # 1) Generate image description with Gemini
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        crop_pil = Image.fromarray(crop)

        # Request a detailed description of the selected region
        description_prompt = "Describe briefly and technically what component of the CUPRA Tavascan dashboard is shown in this image. Be specific and use technical terms. Don't explain the component, just describe it. " + str(crop_pil)
        description_response = model.generate_content([description_prompt, crop_pil])
        image_description = description_response.text.strip()
        
        print(f"Generated description: {image_description}")
        
        # 2) Extract keywords only - modified to get clean output with no introductory text
        keywords_prompt = "Extract exactly 3-5 technical key terms from this text that appear in the official CUPRA Tavascan manual. Return ONLY the terms as a comma-separated list with NO introductory text, NO numbering, and NO bullet points: " + image_description
        keywords_response = model.generate_content(keywords_prompt)
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

        # Debug: Print filtered image paths
        print(len(image_paths))

    return image_paths  # Return the list of image paths


# Si se ejecuta como script principal
if __name__ == "__main__":
    # Obtener la ruta del script actual
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
        text_col, model_text = setup_chromadb(content_dir)
        print("ChromaDB setup successful. Using full RAG capabilities.")
        
        # Load chunks for advanced retrieval functionality
        chunks_path = os.path.join(content_dir, "rag_chunks.json")
        if os.path.exists(chunks_path):
            import json
            with open(chunks_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
            print(f"Loaded {len(chunks)} chunks for retrieval")
        else:
            chunks = None
            print("Warning: rag_chunks.json not found. Advanced retrieval functionality will be limited.")
        
        # Ejemplo de uso del recorte simple
        cropped = crop_image(image, box)
        
        # Uso completo con RAG
        description = get_image_description(image_path, box, model_text=model_text, text_col=text_col, chunks=chunks)
        
        print("\n")

        # Pass the collection and chunks to the retrieve_context function
        retrieval = retrieve_context(
            query=description["description"],
            top_k=20,
            collection=text_col,
            chunks=chunks
        )

        scores = rank_similar_images(cropped, top_k=5, image_paths_list=retrieval)
        print(f"Ranked similar images: {scores}")

        print("Basic retrieval results:")
        print(retrieval)
        
    except Exception as e:
        print(f"ChromaDB setup failed: {e}")
        print("Falling back to basic image description (no RAG).")
        
        # Ejemplo de uso del recorte simple
        cropped = crop_image(image, box)
        
        # Uso básico sin RAG
        description = get_image_description(image_path, box)


