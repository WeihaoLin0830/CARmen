import os
import json
from PIL import Image
from io import BytesIO
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv

# === CONFIGURATION ===
IMAGE_FOLDER = "c:/Users/Claudia/Documents/GitHub/HackUPC_2025/clau/imagenes"
OUTPUT_FILE = "image_descriptions.json"
NUM_ROWS = 3  # Número de filas en la cuadrícula
NUM_COLS = 3  # Número de columnas en la cuadrícula

# === SETUP GEMINI ===
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not set in your .env file.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# === PROMPT DEFINITIONS ===
CAR_INTERIOR_PROMPT = (
    "Provide a structured description of the interior elements of the car visible in the image. "
    "Ignore colors and focus solely on what objects are present and where they are located, "
    "as if the image were divided into a grid (e.g., top-left corner, bottom-center, middle right, etc.). "
    "Only mention objects typically found inside a car, such as: seats, seatbelts, steering wheel, windows, mirrors, "
    "dashboard, screens, buttons, gear stick, glove compartment, doors, handles, etc. "
    "Format your answer as a clear list of objects with their approximate locations."
)

# === HELPER FUNCTIONS ===
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

def split_image_grid(img, rows=3, cols=3):
    width, height = img.size
    cell_width = width // cols
    cell_height = height // rows
    sections = []

    position_labels = {
        0: "top", 1: "middle", 2: "bottom",
        -1: "left", 0: "center", 1: "right"
    }

    for row in range(rows):
        for col in range(cols):
            left = col * cell_width
            upper = row * cell_height
            right = (col + 1) * cell_width if col < cols - 1 else width
            lower = (row + 1) * cell_height if row < rows - 1 else height

            row_label = position_labels.get(row, f"row{row}")
            col_label = position_labels.get(col - 1 if cols == 3 else col, f"col{col}")
            position = f"{row_label}-{col_label}"

            sections.append(((left, upper, right, lower), position))
    return sections

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
        full_description = describe_image(img)

        image_entry = {
            "image_file": filename,
            "description": full_description,
            "sections": []
        }

        grid_sections = split_image_grid(img, NUM_ROWS, NUM_COLS)

        for i, (coords, label) in enumerate(grid_sections):
            cropped = img.crop(coords)
            print(f"   ↳ Describing section {i+1} ({label})")
            section_description = describe_image(cropped)
            image_entry["sections"].append({
                "id": f"{filename}_{i+1}",
                "grid_position": label,
                "description": section_description,
                "coordinates": coords
            })

        all_descriptions.append(image_entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_descriptions, f, indent=2)

    print(f"\n✅ Saved all descriptions to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_all_images()


