<<<<<<< HEAD
import os
import json
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import numpy as np
import cv2
from io import BytesIO
from PIL import Image

# Import your existing chatbot and image processing classes
from chatbot_text import PdfChatbot, get_response_json
from crop_img_bo_retrieve import DashboardImageProcessor, ImageChatSession

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize chatbot with default settings
chatbot = None
image_processor = None
image_chat_session = None

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """Endpoint for text-based chat queries"""
    global chatbot

    data = request.json
    query = data.get('query', '')

    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        # Initialize chatbot if needed
        if chatbot is None:
            try:
                chatbot = PdfChatbot()
                print("Chatbot initialized successfully")
            except Exception as e:
                print(f"Error initializing chatbot: {str(e)}")
                return jsonify({"error": f"Failed to initialize chatbot: {str(e)}"}), 500

        # Add more context to the query for better results
        expanded_query = query  # Ya no expandimos la query para evitar problemas

        # IMPORTANTE: Usar la función correcta del chatbot_text.py
        # Opción 1: Si chatbot.get_response existe directamente:
        try:
            response = chatbot.get_response(query)
        except AttributeError:
            # Opción 2: Si debemos usar get_response_json directamente:
            from chatbot_text import get_response_json
            response = get_response_json(query)

        print(f"Got response: {response[:100]}...")  # Añade logging

        # Try to parse as JSON
        try:
            if isinstance(response, dict):
                # Ya es un diccionario
                return jsonify(response)
            else:
                # Es texto, intentamos parsear como JSON
                response_data = json.loads(response)
                return jsonify(response_data)

        except json.JSONDecodeError:
            # Return raw text if not valid JSON
            return jsonify({
                "answer": response,
                "page_numbers": [],
                "figure_numbers": [],
                "found_info": True
            })

    except Exception as e:
        print(f"Error processing query: {str(e)}")
        import traceback
        traceback.print_exc()  # Muestra el stack trace completo

        return jsonify({
            "answer": "Lo siento, no pude encontrar información específica sobre '" + query + "'. ¿Quieres intentar con otros términos o consultar sobre otra característica del CUPRA Tavascan?",
            "page_numbers": [],
            "figure_numbers": [],
            "found_info": False
        }), 500

@app.route('/api/process-image', methods=['POST'])
def process_image_endpoint():
    """Endpoint for image-based queries"""
    global image_processor
    global image_chat_session

    try:
        data = request.json
        image_data = data.get('image', '')
        query = data.get('query', '')
        box_coordinates = data.get('box', [])

        if not image_data:
            return jsonify({"error": "No image provided"}), 400

        if not query:
            return jsonify({"error": "No query provided"}), 400

        # Initialize image processor if needed
        if image_processor is None:
            try:
                image_processor = DashboardImageProcessor()
                image_chat_session = ImageChatSession()
            except Exception as e:
                return jsonify({"error": f"Failed to initialize image processor: {str(e)}"}), 500

        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if box_coordinates:
            # Convert box coordinates to numpy array
            box = np.array([box_coordinates], dtype=np.int32)

            # Get content directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            content_dir = os.path.join(script_dir, "extracted_content_manual")

            # Setup ChromaDB
            collection, chunks = image_processor.setup_chromadb(content_dir)

            # Retrieve relevant chunks
            reranked_chunks = image_processor._rerank_chunks(chunks, query)

            # Get image context
            image_context = image_processor.get_image_description(image, box)

            # Find similar images
            temp_path = "temp_query_image.jpg"
            cv2.imwrite(temp_path, image[box[0][1]:box[0][3], box[0][0]:box[0][2]])

            # Import and use the rank_similar_images function from similarity_img.py
            from similarity_img import rank_similar_images
            similar_images = rank_similar_images(temp_path)

            # Generate response using the image chat session
            response = image_chat_session.generate_json_response(
                query, reranked_chunks, [image_context], similar_images
            )

            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

            return jsonify(json.loads(response))
        else:
            return jsonify({"error": "No box coordinates provided"}), 400

    except Exception as e:
        return jsonify({"error": f"Error processing image: {str(e)}"}), 500

@app.route('/api/simulator', methods=['POST'])
def simulator_endpoint():
    """Endpoint for 3D simulator queries"""
    # Add simulator-specific logic here if needed
    data = request.json
    frame_index = data.get('frame_index', 0)
    query = data.get('query', '')

    # Sample response - replace with actual implementation
    return jsonify({
        "answer": f"This is a response about frame {frame_index} for query: {query}",
        "page_numbers": [1, 2],
        "figure_numbers": [3]
    })

if __name__ == '__main__':
    app.run(debug=True)
=======
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

>>>>>>> 2667a2761551254abefe2db8532b71b8ea64ade5
