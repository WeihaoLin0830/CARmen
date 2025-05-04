import os
import json
import numpy as np
from PIL import Image, ImageDraw
from sentence_transformers import SentenceTransformer, util

# === CONFIGURATION ===
JSON_PATH = "c:/Users/Claudia/Documents/GitHub/HackUPC_2025/clau/image_descriptions.json"
IMAGE_FOLDER = "c:/Users/Claudia/Documents/GitHub/HackUPC_2025/clau/imagenes"

class ImageSearcher:
    def __init__(self, json_path=JSON_PATH):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"❌ File not found: {json_path}")

        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.data = []
        self.embeddings = []
        self._load_descriptions(json_path)

    def _load_descriptions(self, path):
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)

        all_descriptions = []
        section_map = []

        for item in content:
            image_file = item["image_file"]
            for section in item["sections"]:
                text = section["description"]
                all_descriptions.append(text)
                section_map.append({
                    "image_file": image_file,
                    "description": text,
                    "coordinates": section.get("coordinates"),
                    "section_id": section["id"]
                })

        self.embeddings = self.model.encode(all_descriptions, convert_to_tensor=True)
        self.data = section_map

    def find_best_match_by_description(self, query):
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(query_embedding, self.embeddings)[0].cpu().numpy()

        best_idx = np.argmax(scores)
        best_score = scores[best_idx]

        if best_score < 0.3:
            return None

        best_section = self.data[best_idx]
        best_section["score"] = best_score
        return best_section

# === INTERACTIVE LOOP ===
if __name__ == "__main__":
    searcher = ImageSearcher()
    print("🔎 Image Retrieval: Type a description to find the best matching image section. Type 'exit' to quit.")

    while True:
        query = input("\n🔍 Describe the object or element to locate: ")
        if query.lower() in ["exit", "quit"]:
            break

        best_match = searcher.find_best_match_by_description(query)

        if not best_match:
            print("❌ No matching section found.")
            continue

        image_file = best_match["image_file"]
        print(f"\n✅ Best match found in image: {image_file}")
        print(f"- Section ID: {best_match['section_id']}")
        print(f"- Similarity Score: {best_match['score']:.3f}")
        print(f"- Description: {best_match['description']}")

        # Visualize image with highlighted region
        try:
            img_path = os.path.join(IMAGE_FOLDER, image_file)
            img = Image.open(img_path).convert("RGBA")
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            if best_match.get("coordinates"):
                x1, y1, x2, y2 = best_match["coordinates"]
                draw.rectangle([x1, y1, x2, y2], fill=(0, 255, 0, 120))  # Green overlay

            combined = Image.alpha_composite(img, overlay)
            combined.show(title=f"Best match - {image_file}")
        except Exception as e:
            print(f"⚠️ Could not show image: {e}")
