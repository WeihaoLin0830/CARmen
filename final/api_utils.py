import os
import json
import base64
import numpy as np
import cv2
from io import BytesIO
from PIL import Image

def decode_image(base64_string):
    """
    Decode a base64 image string to a numpy array
    
    Args:
        base64_string: Base64 encoded image string
        
    Returns:
        numpy array image
    """
    try:
        # Handle data URLs (e.g., "data:image/jpeg;base64,...")
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]

        image_bytes = base64.b64decode(base64_string)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image
    except Exception as e:
        raise ValueError(f"Error decoding image: {str(e)}")

def encode_image(image):
    """
    Encode a numpy array image to base64 string
    
    Args:
        image: Numpy array image
        
    Returns:
        Base64 encoded image string
    """
    try:
        # Convert from BGR to RGB for PIL
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        pil_image = Image.fromarray(image)
        buffered = BytesIO()
        pil_image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        raise ValueError(f"Error encoding image: {str(e)}")

def parse_json_response(response_text):
    """
    Parse JSON from response text, handling potential errors
    
    Args:
        response_text: Text containing JSON
        
    Returns:
        Parsed JSON object or fallback object
    """
    try:
        # Try to parse the JSON directly
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If direct parsing fails, try to extract JSON using regex
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass

        # Fallback to a simple structure
        return {
            "answer": response_text,
            "page_numbers": [],
            "figure_numbers": []
        }

def find_content_dir():
    """
    Find the content directory containing extracted PDF content
    
    Returns:
        Path to content directory or None if not found
    """
    # Get current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Check for extracted_content in current directory
    if os.path.exists(os.path.join(script_dir, "extracted_content_manual")):
        return os.path.join(script_dir, "extracted_content_manual")

    # Check parent directory
    parent_dir = os.path.dirname(script_dir)
    if os.path.exists(os.path.join(parent_dir, "extracted_content_manual")):
        return os.path.join(parent_dir, "extracted_content_manual")

    # Look for directories matching pattern
    for directory in os.listdir(script_dir):
        if directory.startswith("extracted_content"):
            return os.path.join(script_dir, directory)

    return None