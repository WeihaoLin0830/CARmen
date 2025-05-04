import os
import json
from PIL import Image
from io import BytesIO
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv

# === CONFIGURACIÓN ===
IMAGE_FOLDER = "c:/Users/Claudia/Documents/GitHub/HackUPC_2025/clau/imagenes"
OUTPUT_FILE = "image_descriptions.json"

# === SETUP GEMINI ===
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not set in your .env file.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# === NUEVO PROMPT ===
CAR_INTERIOR_PROMPT = (
    "Look at the image and identify the 5 most important interior elements of the vehicle, "
    "such as seats, seatbelts, steering wheel, dashboard, mirrors, gear stick, etc. "
    "Only include objects that are clearly part of the vehicle's interior. "
    "List the objects in order of importance from most to least, and number them from 1 to 5. "
    "Do not include colors, locations, or other metadata. Just the object names in a clean list."
)

# === FUNCIONES AUXILIARES ===
def image_to_bytes(pil_image):
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    return {"mime_type": "image/png", "data": buf.getvalue()}

def describe_image(pil_img, prompt=CAR_INTERIOR_PROMPT):
    try:
        response = model.generate_content([prompt, image_to_bytes(pil_img)])
        return response.text.strip()
    except Exception as e:
        return f"Error: {e}"

# === FUNCIÓN PRINCIPAL ===
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

        print(f"🧠 Describing image: {filename}")
        full_description = describe_image(img)

        image_entry = {
            "image_file": filename,
            "description": full_description
        }

        all_descriptions.append(image_entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_descriptions, f, indent=2)

    print(f"\n✅ Saved all descriptions to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_all_images()
