import os
import json 

import re
import time
import numpy as np
import cv2

def get_image_paths(image_ids):
    """
    Given a list of image IDs, return the paths of the images
    located in the extracted_content_manual/images directory.
    If the image ID is a number, it will count the images and select the nth image.
    """
    content_dir = "extracted_content_manual"  # Define the base directory
    image_dir = os.path.join(content_dir, "images")
    image_paths = []

    all_images = sorted(os.listdir(image_dir))
    result = []

    for i in image_ids:
        result.append(all_images[i-1])
        
    return result
# Test with images 11, 2, and 3 by their position in the sorted list
x = get_image_paths([11, 2, 3])

print(x)