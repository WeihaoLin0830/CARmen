import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

# === CONFIGURATION ===
JSON_PATH = "c:/Users/Claudia/Documents/GitHub/HackUPC_2025/clau/image_descriptions.json"

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

    def search(self, query, top_k=1):
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(query_embedding, self.embeddings)[0]
        top_indices = np.argsort(-scores.cpu().numpy())[:top_k]

        results = []
        for idx in top_indices:
            match = self.data[idx]
            match["score"] = float(scores[idx])
            results.append(match)
        return results

# === SAFE ENTRY POINT ===
if __name__ == "__main__":
    start = input("🔎 Press ENTER to start the image search, or type 'exit' to cancel: ")
    if start.strip().lower() == "exit":
        print("❌ Search cancelled.")
    else:
        searcher = ImageSearcher()
        while True:
            user_query = input("\nQuery (or 'exit'): ")
            if user_query.lower() in ["exit", "quit"]:
                print("👋 Exiting.")
                break
            result = searcher.search(user_query)[0]
            print(f"\n🔍 Best match:")
            print(f"Image: {result['image_file']}")
            print(f"Section: {result['description']}")
            print(f"Score: {result['score']:.3f}")
            if result.get("coordinates"):
                print(f"Coordinates: {result['coordinates']}")
            print("-" * 50)

