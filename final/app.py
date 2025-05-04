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