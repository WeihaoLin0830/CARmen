# Import libraries at the beginning
import json
import sys
import os
from chatbot_text import get_response_json
import re
import numpy as np
import cv2
import time
from crop_img_bo_retrieve import DashboardImageProcessor, ImageChatSession, _rerank_chunks, retrieve_context
from similarity_img import rank_similar_images
from flask import Flask, request, jsonify
from flask_cors import CORS

# Global variables for pre-loaded resources
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
content_dir = os.path.join(parent_dir, "extracted_content_manual")

# Pre-initialize all heavy resources
print("Inicializando recursos...")
start_time = time.time()

try:
    # Initialize processor
    processor = DashboardImageProcessor()

    # Setup ChromaDB
    text_col, model_text = processor.setup_chromadb(content_dir)

    # Load chunks for retrieval
    chunks = processor.load_chunks(content_dir)

    # Make content_dir available to imported functions
    sys.modules['crop_img_bo_retrieve'].content_dir = content_dir

    # Create chat session
    chat_session = ImageChatSession()

    # Initialize chatbot
    chatbot = get_response_json()

    print(f"Recursos cargados correctamente en {time.time() - start_time:.2f} segundos")
    resources_loaded = True

except Exception as e:
    print(f"Error al cargar recursos: {str(e)}")
    resources_loaded = False

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def get_image_paths(image_ids):
    """
    Given a list of image IDs, return the paths of the images
    located in the extracted_content_manual/images directory.
    """
    image_dir = os.path.join(content_dir, "images")
    image_paths = []

    for image_id in image_ids:
        image_path = os.path.join(image_dir, f"{image_id}.jpg")
        if os.path.exists(image_path):
            image_paths.append(image_path)
        else:
            print(f"Image not found: {image_path}")

    return image_paths

def main(query):
    """
    Function to handle text queries.
    Returns JSON response.
    """
    if not query.strip():
        return {"error": "No question provided", "answer": "", "page_numbers": [], "figure_numbers": []}

    try:
        response_text = chatbot.get_response(query, top_k=3)

        try:
            response_clean = re.sub(r'```json', '', response_text)
            response_clean = re.sub(r'```', '', response_clean)
            response = json.loads(response_clean)

        except json.JSONDecodeError:
            # Return a fallback JSON if parsing fails
            response = {
                "answer": response_text,
                "page_numbers": [],
                "figure_numbers": []
            }

        return response
    except Exception as e:
        return {"error": str(e), "answer": "", "page_numbers": [], "figure_numbers": []}

def image(image_path, box_coordinates):
    """
    Function to handle image input and output.
    Uses pre-loaded resources for instant response.
    Accepts image_path and box_coordinates as parameters.
    """

    # Ensure the image path is relative to the ../cupra_frames/ directory
    full_image_path = os.path.join(parent_dir, "Hui", "cupra_frames", image_path)
    print(f"Processing image at path: {full_image_path}")
    print(f"Box coordinates: {box_coordinates}")

    if not resources_loaded:
        return {"answer": "Error: Los recursos no se han cargado correctamente",
                "page_numbers": [], "figure_numbers": []}

    try:
        start_time = time.time()

        # Check if file exists before processing
        if not os.path.exists(full_image_path):
            error_msg = f"Image file not found: {full_image_path}"
            print(error_msg)
            return {"error": error_msg, "answer": "", "page_numbers": [], "figure_numbers": []}

        # Convert box coordinates to numpy array
        box = np.array([box_coordinates], dtype=np.int32)

        # Get image description - using pre-loaded processor
        description = processor.get_image_description(full_image_path, box)

        # Use retrieve_context with pre-loaded resources
        image_paths_list, image_contexts = retrieve_context(
            query=description["description"],
            top_k=20,
            collection=text_col,
            chunks=chunks
        )

        # Get cropped image - check if image exists first
        image = cv2.imread(full_image_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image from {full_image_path}")

        cropped = processor.crop_image(image, box)

        # Rank similar images
        scores = rank_similar_images(cropped, top_k=3, image_paths_list=image_paths_list)

        # Extract page numbers from image contexts
        top_pages = list(set([image_contexts[img[0]][0] for img in scores if img[0] in image_contexts]))

        # Collect chunks from top pages using pre-loaded chunks
        all_chunks_from_pages = [
            chunk for chunk in chunks if chunk["start_page"] in top_pages
        ]


        # Re-rank chunks based on description
        reranked_chunks = _rerank_chunks(all_chunks_from_pages, description["description"], top_k=3)


        # Generate JSON response using pre-loaded chat session
        json_response = chat_session.generate_json_response(
            description["description"],
            reranked_chunks,
            image_contexts,
            scores
        )

        #print(f"\nJSON Response generated successfully: {json_response}")
        #print(f"Processing completed in {time.time() - start_time:.2f} seconds")
        #print(f"Response: {json_response}

        if "figure_numbers" in json_response:
            image_ids = json_response["figure_numbers"]
            image_paths = get_image_paths(image_ids)
            json_response["image_paths"] = image_paths
            
        return json_response

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in image processing: {str(e)}")
        print(f"Error details: {error_details}")
        return {
            "error": str(e),
            "answer": f"Error procesando imagen: {str(e)}",
            "page_numbers": [],
            "figure_numbers": []
        }

# API Routes
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """API endpoint for chat queries"""
    data = request.get_json()

    if not data or 'query' not in data:
        return jsonify({"error": "No query provided in request"}), 400

    query = data['query']
    response = main(query)
    return jsonify(response)

@app.route('/image', methods=['POST'])
def image_endpoint():
    """API endpoint for image analysis"""
    print("\n--- New image analysis request received ---")
    try:
        data = request.get_json()
        print(f"Request data: {data}")

        if not data or 'image_path' not in data or 'box' not in data:
            error_msg = "Missing image_path or box in request"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        image_path = data['image_path']
        box_coordinates = data['box']

        # Validate box format
        if not isinstance(box_coordinates, list) or len(box_coordinates) != 4:
            error_msg = "Box must be a list of 4 integers [x0, y0, x1, y1]"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        print(f"Calling image function with path {image_path} and box {box_coordinates}")
        response = image(image_path, box_coordinates)
        print(f"Response from image function: {response}")

        # Convert to ensure JSON serialization works
        json_response = jsonify(response)
        print("JSON response created successfully")

        # Retrieve image paths for the top-ranked images
        if "figure_numbers" in response:
            image_ids = response["figure_numbers"]
            image_paths = get_image_paths(image_ids)
            response["image_paths"] = image_paths

        return json_response

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Exception in image_endpoint: {str(e)}")
        print(f"Traceback: {error_details}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    if resources_loaded:
        # Run Flask app in development mode
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("No se puede ejecutar la API debido a errores en la carga de recursos")