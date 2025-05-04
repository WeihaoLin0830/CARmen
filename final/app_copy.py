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
from flask import Flask, request, jsonify, render_template, send_from_directory
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

def image(image_path, box_coordinates):
    """
    Process an image with the given box coordinates.
    Returns JSON response with analysis results.
    """
    try:
        # Convert box coordinates to integers
        x1, y1, x2, y2 = map(int, box_coordinates)

        # Load the image
        img = cv2.imread(image_path)
        if img is None:
            return {"error": f"Could not load image from {image_path}"}

        # Crop the image based on box coordinates
        cropped_img = img[y1:y2, x1:x2]

        # Use chat session to process the image
        result = chat_session.process_image(cropped_img)

        return result
    except Exception as e:
        print(f"Error in image(): {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "answer": "Lo siento, no pude analizar esta parte de la imagen. ¿Puedo ayudarte con algo más?"}

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
        print(f"Error en main(): {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "answer": "Lo siento, no pude encontrar información específica sobre eso. ¿Puedo ayudarte con algo más sobre tu CUPRA Tavascan?", "page_numbers": [], "figure_numbers": []}

# Añade estas rutas y el código para iniciar el servidor al final del archivo

# Página principal - Sirve el HTML
@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')

# API Routes
@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """API endpoint for chat queries"""
    data = request.get_json()
    print(f"Recibida solicitud de chat: {data}")

    if not data or 'query' not in data:
        return jsonify({"error": "No query provided in request"}), 400

    query = data['query']
    response = main(query)
    return jsonify(response)

@app.route('/api/image', methods=['POST'])
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

        print(f"Calling image function with path {image_path} and box {box_coordinates}")
        response = image(image_path, box_coordinates)
        print(f"Response from image function: {response}")

        return jsonify(response)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Exception in image_endpoint: {str(e)}")
        print(f"Traceback: {error_details}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Servir archivos estáticos de cupra_frames
@app.route('/cupra_frames/<path:filename>')
def serve_cupra_frame(filename):
    return send_from_directory(os.path.join(script_dir, 'static', 'cupra_frames'), filename)

# IMPORTANTE: Código para iniciar el servidor
if __name__ == "__main__":
    if resources_loaded:
        print("Servidor iniciado en http://localhost:5000")
        # Run Flask app in development mode
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("No se puede ejecutar la API debido a errores en la carga de recursos")