import os
import json
import numpy as np
from collections import defaultdict
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

    def find_extremes_by_object(self, query):
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(query_embedding, self.embeddings)[0].cpu().numpy()

        image_hits = defaultdict(list)

        for idx, score in enumerate(scores):
            if score > 0.3:  # Umbral configurable
                section = self.data[idx]
                image_file = section["image_file"]
                image_hits[image_file].append((score, section))

        if not image_hits:
            return None, None

        max_img = max(image_hits.items(), key=lambda x: len(x[1]))
        min_img = min([i for i in image_hits.items() if len(i[1]) > 0], key=lambda x: len(x[1]))

        return max_img, min_img

# === INTERACTIVE LOOP ===
if __name__ == "__main__":
    searcher = ImageSearcher()
    print("🔎 Image Retrieval: Type object to find. Type 'exit' to quit.")

    while True:
        query = input("\n🔍 Object to locate (e.g., 'steering wheel'): ")
        if query.lower() in ["exit", "quit"]:
            break

        max_img, min_img = searcher.find_extremes_by_object(query)

        if not max_img and not min_img:
            print("❌ No matching sections found.")
            continue

        for label, img_data in [("🟥 Most widespread", max_img), ("🟩 Most focused", min_img)]:
            image_file, sections = img_data
            print(f"\n{label} → {image_file} ({len(sections)} sections mentioning '{query}')")
            for s in sections:
                print(f"- Section ID: {s[1]['section_id']}, Score: {s[0]:.3f}")
                print(f"  Text: {s[1]['description'][:120]}...")

            try:
                img_path = os.path.join(IMAGE_FOLDER, image_file)
                img = Image.open(img_path).convert("RGBA")
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)

                for s in sections:
                    if s[1].get("coordinates"):
                        x1, y1, x2, y2 = s[1]["coordinates"]
                        draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 100))

                combined = Image.alpha_composite(img, overlay)
                combined.show(title=f"{label} - {image_file}")
            except Exception as e:
                print(f"⚠️ Could not show image: {e}")



