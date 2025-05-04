import os
import json
import logging
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Define the default content directory
DEFAULT_CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sergi", "extracted_content_manual")

# Flag for using mock responses (for testing without dependencies)
USE_MOCK_RESPONSES = False

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify the API is running"""
    return jsonify({
        "status": "ok",
        "message": "API is running"
    })

@app.route('/api/text-query', methods=['POST'])
def text_query():
    """
    API endpoint for text queries to the chatbot
    
    Expected JSON body:
    {
        "query": "text query about the Cupra manual",
        "model_name": "gemini-2.0-flash", (optional)
        "top_k": 3 (optional)
    }
    
    Returns:
    JSON response with answer, page_numbers, and figure_numbers
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    if "query" not in data:
        return jsonify({"error": "Missing required parameter: query"}), 400
    
    query = data["query"]
    model_name = data.get("model_name", "gemini-2.0-flash")
    top_k = data.get("top_k", 3)
    content_dir = data.get("content_dir", DEFAULT_CONTENT_DIR)
    
    # Mock response for testing without dependencies
    if USE_MOCK_RESPONSES:
        logger.info(f"Generating mock response for: '{query}'")
        return jsonify({
            "answer": f"This is a mock response to your query: '{query}'",
            "page_numbers": [10, 25, 42],
            "figure_numbers": ["Fig. 3.2"]
        })
    
    try:
        # Check if the content directory exists
        if not os.path.exists(content_dir):
            logger.error(f"Content directory not found: {content_dir}")
            return jsonify({
                "error": f"Content directory not found: {content_dir}"
            }), 404
            
        # Import here to avoid dependency issues during testing
        from sergi.chatbot_text import get_response_json
        
        logger.info(f"Processing query: '{query}' with model: {model_name}, top_k: {top_k}")
        response = get_response_json(query, content_dir, model_name, top_k)
        logger.info(f"Generated response successfully")
        return jsonify(response)
        
    except ModuleNotFoundError as e:
        logger.error(f"Module not found: {str(e)}")
        return jsonify({
            "error": f"Required module not found: {str(e)}. Please check if all dependencies are installed."
        }), 500
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        return jsonify({"error": f"File not found: {str(e)}"}), 404
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return jsonify({"error": "Invalid JSON format in response"}), 500
    except Exception as e:
        logger.error(f"Error processing text query: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/api/image-query', methods=['POST'])
def image_query():
    """
    API endpoint for image component analysis
    
    Expected JSON body:
    {
        "image_path": "path/to/image.png",
        "box_coordinates": [x0, y0, x1, y1]
    }
    
    Returns:
    JSON response with component description and related information
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    if "image_path" not in data:
        return jsonify({"error": "Missing required parameter: image_path"}), 400
    
    if "box_coordinates" not in data:
        return jsonify({"error": "Missing required parameter: box_coordinates"}), 400
    
    image_path = data["image_path"]
    box_coordinates = np.array([data["box_coordinates"]], dtype=np.int32)
    content_dir = data.get("content_dir", DEFAULT_CONTENT_DIR)
    
    # Mock response for testing without dependencies
    if USE_MOCK_RESPONSES:
        logger.info(f"Generating mock response for image: {image_path}")
        return jsonify({
            "component_name": "Mock Component",
            "description": "This is a mock response for image component analysis",
            "related_pages": [15, 22],
            "function": "Mock function description"
        })
    
    try:
        # Check if the image file exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return jsonify({"error": f"Image file not found: {image_path}"}), 404
            
        # Import here to avoid dependency issues during testing
        from sergi.crop_img_bo_retrieve_resum import process_dashboard_component
        
        logger.info(f"Processing image: {image_path}, box coordinates: {box_coordinates}")
        response = process_dashboard_component(image_path, box_coordinates, content_dir)
        logger.info(f"Image processing successful")
        return jsonify(response)
        
    except ModuleNotFoundError as e:
        logger.error(f"Module not found: {str(e)}")
        return jsonify({
            "error": f"Required module not found: {str(e)}. Please check if all dependencies are installed."
        }), 500
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        return jsonify({"error": f"File not found: {str(e)}"}), 404
    except Exception as e:
        logger.error(f"Error processing image query: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# Simple test interface
@app.route('/', methods=['GET'])
def index():
    """Provide a simple test interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cupra Manual API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            .endpoint { background: #f7f7f7; padding: 10px; margin: 10px 0; border-radius: 5px; }
            code { background: #eee; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>Cupra Manual API</h1>
        <p>API endpoints available:</p>
        <div class="endpoint">
            <h3>Health Check</h3>
            <p><code>GET /api/health</code> - Check if the API is running</p>
        </div>
        <div class="endpoint">
            <h3>Text Query</h3>
            <p><code>POST /api/text-query</code> - Ask questions about the Cupra manual</p>
        </div>
        <div class="endpoint">
            <h3>Image Query</h3>
            <p><code>POST /api/image-query</code> - Analyze dashboard components</p>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Set mock response mode from environment variable
    USE_MOCK_RESPONSES = os.environ.get('USE_MOCK_RESPONSES', 'False').lower() == 'true'
    if USE_MOCK_RESPONSES:
        logger.info("Running in MOCK mode - all responses will be simulated")
    
    # Print startup information
    logger.info(f"Starting Cupra Manual API server")
    logger.info(f"Content directory: {DEFAULT_CONTENT_DIR}")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
