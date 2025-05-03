import os
import json
from PIL import Image
from io import BytesIO
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv

# === CONFIGURATION ===
IMAGE_FOLDER = "c:/Users/Claudia/Documents/GitHub/HackUPC_2025/clau/imagenes"  # Change if needed
OUTPUT_FILE = "image_descriptions.json"
SUBSECTIONS_PER_IMAGE = 4  # 4 = split into 4 quadrants

# === SETUP GEMINI ===
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not set in your .env file.")

genai.configure(api_key=api_key)

# ✅ Use updated model
model = genai.GenerativeModel("models/gemini-1.5-flash")

# === HELPER FUNCTIONS ===
def image_to_bytes(pil_image):
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    return {"mime_type": "image/png", "data": buf.getvalue()}

def describe_image(pil_img, prompt="Describe this image in English in detail."):
    try:
        response = model.generate_content([prompt, image_to_bytes(pil_img)])
        return response.text.strip()
    except Exception as e:
        return f"Error: {e}"

def split_image_quadrants(img):
    width, height = img.size
    mid_x, mid_y = width // 2, height // 2
    return [
        (0, 0, mid_x, mid_y),               # Top-left
        (mid_x, 0, width, mid_y),           # Top-right
        (0, mid_y, mid_x, height),          # Bottom-left
        (mid_x, mid_y, width, height)       # Bottom-right
    ]

# === MAIN FUNCTION ===
def process_all_images():
    if not os.path.exists(IMAGE_FOLDER):
        raise FileNotFoundError(f"❌ Folder not found: {IMAGE_FOLDER}")

    all_descriptions = []

    for filename in tqdm(os.listdir(IMAGE_FOLDER), desc="Processing images"):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        filepath = os.path.join(IMAGE_FOLDER, filename)
        try:
            img = Image.open(filepath).convert("RGB")
        except Exception as e:
            print(f"⚠️ Could not open {filename}: {e}")
            continue

        print(f"🧠 Describing full image: {filename}")
        full_description = describe_image(img, "Describe this image in English in detail.")

        image_entry = {
            "image_file": filename,
            "description": full_description,
            "sections": []
        }

        coords_list = split_image_quadrants(img)[:SUBSECTIONS_PER_IMAGE]

        for i, coords in enumerate(coords_list):
            cropped = img.crop(coords)
            print(f"   ↳ Describing section {i+1}")
            section_description = describe_image(cropped, "Describe this section of the image in English in detail.")
            image_entry["sections"].append({
                "id": f"{filename}_{i+1}",
                "description": section_description,
                "coordinates": coords
            })

        all_descriptions.append(image_entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_descriptions, f, indent=2)

    print(f"\n✅ Saved all descriptions to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_all_images()

