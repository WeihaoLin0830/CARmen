import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import base64

API_KEY = "4abJigJ5xBlkZA4bDx6F"
WORKSPACE = "hackupc-70ysk"
WORKFLOW_ID = "small-object-detection-sahi-3"
IMAGE_PATH = "clau\imagenes\cap1.png"

try:
    # Get absolute path for reliable file access
    abs_image_path = os.path.abspath(IMAGE_PATH)
    
    # Convert image to base64 for API
    with open(abs_image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Prepare the request payload
    payload = {
        "api_key": API_KEY,
        "inputs": {
            "image": {
                "type": "base64",
                "value": image_data
            }
        }
    }
    
    # Make API request
    url = f"https://serverless.roboflow.com/infer/workflows/{WORKSPACE}/{WORKFLOW_ID}"
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending request to {url}...")
    response = requests.post(url, headers=headers, json=payload)
    
    # Check response
    if response.status_code == 200:
        result = response.json()

        # Check response
        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2))
            
            # Save the JSON result to a file
            json_output_path = os.path.join(os.path.dirname(abs_image_path), "detection_result.json")
            with open(json_output_path, 'w') as json_file:
                json.dump(result, json_file, indent=2)
            print(f"Saved JSON result to: {json_output_path}")
            
            # Process and display results
            img = Image.open(abs_image_path).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Rest of your code remains the same...

        print(json.dumps(result, indent=2))
        
        # Process and display results
        img = Image.open(abs_image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        # Get the actual image dimensions
        img_width, img_height = img.size
        print(f"Actual image dimensions: {img_width}x{img_height}")

        # Get API-reported image dimensions
        api_img = result.get("predictions", {}).get("image", {})
        api_width = api_img.get("width", 400)
        api_height = api_img.get("height", 400)
        print(f"API-reported dimensions: {api_width}x{api_height}")
        
        # Calculate scaling factors
        scale_x = img_width / api_width
        scale_y = img_height / api_height
        print(f"Scaling factors: x={scale_x}, y={scale_y}")

                # Check if we have predictions
        # Original incorrect path
        # predictions = result.get("predictions", {}).get("predictions", [])
        
        # Correct path to access predictions - they are nested inside the first item of the predictions array
        predictions = result.get("predictions", [])[0].get("predictions", {}).get("predictions", []) if result.get("predictions") else []
        print(f"Found {len(predictions)} objects")
        
        if len(predictions) == 0:
            print("No objects detected in the image!")
        
        for prediction in predictions:
            # Scale coordinates to match actual image size
            x = prediction["x"] * scale_x
            y = prediction["y"] * scale_y
            w = prediction["width"] * scale_x
            h = prediction["height"] * scale_y
            
            label = prediction["class"]
            conf = prediction["confidence"]
            
            print(f"Drawing box for {label} at scaled ({x}, {y}) with size {w}x{h}")

            # Convert to box corners
            x0 = x - w / 2
            y0 = y - h / 2
            x1 = x + w / 2
            y1 = y + h / 2

            # Draw more noticeable borders
            draw.rectangle([x0, y0, x1, y1], outline="red", width=4)
            
            # Draw a semi-transparent background for text
            text = f"{label} ({conf:.2f})"
            draw.rectangle([x0, y0-20, x0+100, y0], fill=(255, 0, 0, 128))
            draw.text((x0, y0-15), text, fill="white")

        # Save the image with boxes for verification
        output_path = os.path.join(os.path.dirname(abs_image_path), "output_detection.png")
        img.save(output_path)
        print(f"Saved output image to: {output_path}")
        
        # Show the image
        img.show()
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    
except Exception as e:
    print(f"❌ Error: {e}")