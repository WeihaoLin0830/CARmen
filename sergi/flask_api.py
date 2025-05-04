from flask import Flask, request, jsonify, render_template
import os
import json
import numpy as np
import cv2
from werkzeug.utils import secure_filename
import base64
import re
import sys
from dotenv import load_dotenv
import shutil

# Import your modules
# Updated to import the classes directly
from chatbot_text import get_response_json, PdfChatbot
from crop_img_bo_retrieve import DashboardImageProcessor, ImageChatSession, _rerank_chunks

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create templates directory and ensure index.html is there
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

# Check if index.html exists in project root and copy it to templates if needed
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE_HTML = os.path.join(PROJECT_ROOT, 'index.html')
TARGET_HTML = os.path.join(TEMPLATE_DIR, 'index.html')

if os.path.exists(SOURCE_HTML) and not os.path.exists(TARGET_HTML):
    shutil.copy(SOURCE_HTML, TARGET_HTML)
    print(f"Copied index.html to templates directory: {TARGET_HTML}")

# Helper function to check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Find the content directory
def find_content_dir():
    # Look for directories that match the pattern "extracted_content_*"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    potential_dirs = []
    
    for item in os.listdir(current_dir):
        if os.path.isdir(os.path.join(current_dir, item)) and item.startswith("extracted_content_"):
            potential_dirs.append(os.path.join(current_dir, item))
            
    if not potential_dirs:
        return None
        
    if len(potential_dirs) == 1:
        return potential_dirs[0]
        
    # If multiple directories found, use the first one
    return potential_dirs[0]

CONTENT_DIR = find_content_dir()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/text_query', methods=['POST'])
def text_query():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    query = data['query']
    top_k = data.get('top_k', 3)
    model_name = data.get('model_name', 'gemini-2.0-flash')
    
    try:
        # Call your PDF chatbot function
        response = get_response_json(query, content_dir=CONTENT_DIR, model_name=model_name, top_k=top_k)
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/image_query', methods=['POST'])
def image_query():
    # Check if the post request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed types: png, jpg, jpeg'}), 400
    
    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Get box coordinates
        box_str = request.form.get('box_coordinates', '')
        if box_str:
            # Parse the box coordinates (format: "x0,y0,x1,y1")
            coords = [int(coord) for coord in box_str.split(',')]
            if len(coords) != 4:
                return jsonify({'error': 'Invalid box coordinates format. Use "x0,y0,x1,y1"'}), 400
            
            box_coordinates = [[coords[0], coords[1], coords[2], coords[3]]]
        else:
            # If no coordinates provided, use the entire image
            img = cv2.imread(filepath)
            height, width = img.shape[:2]
            box_coordinates = [[0, 0, width, height]]
        
        # Process the dashboard component
        result = process_dashboard_component(filepath, box_coordinates, content_dir=CONTENT_DIR)
        
        # Add base64 of the cropped image to response
        img = cv2.imread(filepath)
        crop = img[box_coordinates[0][1]:box_coordinates[0][3], box_coordinates[0][0]:box_coordinates[0][2]]
        _, buffer = cv2.imencode('.jpg', crop)
        crop_base64 = base64.b64encode(buffer).decode('utf-8')
        result['image_data'] = f"data:image/jpeg;base64,{crop_base64}"
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat_session', methods=['POST'])
def chat_session():
    """Handle a chat session with history"""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    query = data['query']
    history = data.get('history', [])
    
    try:
        # Initialize a persistent chatbot session
        chatbot = PdfChatbot(content_dir=CONTENT_DIR, model_name='gemini-2.0-flash')
        
        # If there's history, replay it to build up context
        for past_msg in history:
            if past_msg['role'] == 'user':
                # Just process past messages to build context, but don't save responses
                _ = chatbot.get_response(past_msg['content'])
        
        # Get response for the current query
        response = chatbot.get_response(query)
        
        # Clean the JSON response if possible
        try:
            response_clean = re.sub(r'```json', '', response)
            response_clean = re.sub(r'```', '', response_clean)
            json_response = json.loads(response_clean)
            return jsonify(json_response)
        except json.JSONDecodeError:
            # Return text response if not valid JSON
            return jsonify({
                'answer': response,
                'page_numbers': [],
                'figure_numbers': []
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Define the process_dashboard_component function using the DashboardImageProcessor class
def process_dashboard_component(image_path, box_coordinates, content_dir=None):
    """
    Process a dashboard component image using the DashboardImageProcessor class
    
    Args:
        image_path: Path to the uploaded image
        box_coordinates: Array of coordinates [x0, y0, x1, y1]
        content_dir: Directory with extracted content
        
    Returns:
        JSON response with information about the dashboard component
    """
    try:
        # Initialize the processor
        processor = DashboardImageProcessor()
        
        # Setup ChromaDB if content_dir is provided
        if content_dir:
            text_col, model_text = processor.setup_chromadb(content_dir)
            chunks = processor.load_chunks(content_dir)
        else:
            text_col, chunks = None, None
        
        # Load the image
        image = cv2.imread(image_path)
        
        # Process the cropped region
        cropped = processor.crop_image(image, box_coordinates)
        
        # Get image description
        description = processor.get_image_description(image_path, box_coordinates)
        
        if text_col and chunks:
            # Use the retrieve_context function to get similar images
            from crop_img_bo_retrieve import retrieve_context
            image_paths_list, image_contexts = retrieve_context(
                query=description["description"],
                top_k=20,
                collection=text_col,
                chunks=chunks
            )
            
            # Rank similar images
            from similarity_img import rank_similar_images
            scores = rank_similar_images(cropped, top_k=3, image_paths_list=image_paths_list)
            
            # Extract page numbers from image contexts
            top_pages = list(set([image_contexts[img[0]][0] for img in scores if img[0] in image_contexts]))
            
            # Collect all chunks from the top pages
            all_chunks_from_pages = [
                chunk for chunk in chunks if chunk["start_page"] in top_pages
            ]
            
            # Re-rank the chunks based on the query
            reranked_chunks = _rerank_chunks(all_chunks_from_pages, description["description"], top_k=3)
            
            # Initialize chat session and generate JSON response
            chat_session = ImageChatSession()
            json_response = chat_session.generate_json_response(
                description["description"],
                reranked_chunks,
                image_contexts,
                scores
            )
            
            return json_response
        else:
            # Basic response without RAG
            return {
                "answer": f"Component identified: {description['description']}",
                "key_terms": description["key_terms"],
                "page_numbers": [],
                "figure_numbers": []
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "answer": "Error processing dashboard component. Please try again.",
            "page_numbers": [],
            "figure_numbers": []
        }

if __name__ == '__main__':
    # Templates directory should already exist from earlier code
    print(f"Starting Flask app. API will be available at http://127.0.0.1:5000/")
    app.run(debug=True)