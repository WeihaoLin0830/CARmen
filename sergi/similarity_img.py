import numpy as np
import cv2
import os
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import re  # Added for regex pattern matching
import torch
from pathlib import Path
import matplotlib.pyplot as plt
from transformers import CLIPProcessor, CLIPModel

# Load environment variables
load_dotenv()

# Initialize CLIP model
model_name = "openai/clip-vit-base-patch32"
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Load CLIP model and processor
clip_model = CLIPModel.from_pretrained(model_name).to(device)
clip_processor = CLIPProcessor.from_pretrained(model_name)

# --- Ranking de imágenes por similitud visual ---
# Directorio de imágenes del manual
images_folder = "../extracted_content_manual/images"  # Updated default path

def rank_similar_images(input_image, top_k=5, image_paths_list=None):
    """Rank manual images by similarity to input image"""
    # Si input_image es un array (ej: crop), convertir a PIL Image
    if isinstance(input_image, np.ndarray):
        input_pil = Image.fromarray(input_image)
        # Guardar temporalmente
        temp_path = "temp_query_image.jpg"
        input_pil.save(temp_path)
        query_path = temp_path
    else:
        # Si ya es una ruta
        query_path = input_image

    # Obtener embedding de la imagen query con el mismo modelo CLIP ya cargado
    try:
        inputs_query = clip_processor(images=Image.open(query_path).convert("RGB"), return_tensors="pt").to(device)
        with torch.no_grad():
            query_emb = clip_model.get_image_features(**inputs_query)
            query_emb = query_emb / query_emb.norm(p=2, dim=-1, keepdim=True)
        query_emb = query_emb.cpu().numpy()[0]
        print(f"Successfully processed query image: {query_path}")
    except Exception as e:
        print(f"Error processing query image {query_path}: {str(e)}")
        return []

    # Procesar todas las imágenes en el directorio o lista proporcionada
    similarities = []
    if image_paths_list is None:
        print(f"Looking for images in folder: {images_folder}")
        image_paths = list(Path(images_folder).glob("*.jpeg")) + list(Path(images_folder).glob("*.jpg")) + list(Path(images_folder).glob("*.png"))
        print(f"Found {len(image_paths)} images in folder")
    else:
        # Convert string paths to Path objects, normalize Windows paths
        image_paths = []
        print(f"Processing {len(image_paths_list)} provided image paths")
        for p in image_paths_list:
            # Handle string paths by normalizing and converting to Path
            if isinstance(p, str):
                # Convert Windows backslashes to forward slashes
                norm_path = p.replace('\\', '/')
                image_paths.append(Path(norm_path))
                print(f"Added normalized path: {norm_path}")
            else:
                image_paths.append(p)

    # Print the first few paths for debugging
    if image_paths:
        print("First few image paths:")
        for p in image_paths[:3]:
            print(f"  - {p} (exists: {p.exists()})")
    else:
        print("Warning: No image paths found to process")
        return []

    for img_path in image_paths:
        try:
            img = Image.open(img_path).convert("RGB")
            inputs = clip_processor(images=img, return_tensors="pt").to(device)
            with torch.no_grad():
                img_emb = clip_model.get_image_features(**inputs)
                img_emb = img_emb / img_emb.norm(p=2, dim=-1, keepdim=True)
            img_emb = img_emb.cpu().numpy()[0]

            # Calcular similitud
            similarity = np.dot(query_emb, img_emb)
            similarities.append((str(img_path), similarity, img))
        except Exception as e:
            print(f"Error processing {img_path}: {e}")

    # Ordenar por similitud (descendente)
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Visualizar resultados
    n_images = min(top_k + 1, len(similarities) + 1)

    # Manejo especial si no hay suficientes imágenes
    if n_images <= 1:
        fig, ax = plt.subplots(figsize=(5, 5))
        if isinstance(input_image, np.ndarray):
            ax.imshow(cv2.cvtColor(input_image, cv2.COLOR_RGB2BGR))
        else:
            ax.imshow(Image.open(query_path))
        ax.set_title("Query Image")
        ax.axis('off')
    else:
        fig, axes = plt.subplots(1, n_images, figsize=(15, 4))

        # Asegúrate de que axes es siempre una lista
        if n_images == 2:  # Solo 2 imágenes (query + 1 similar)
            axes = [axes[0], axes[1]]

        # Imagen query
        if isinstance(input_image, np.ndarray):
            axes[0].imshow(input_image)  # Ya está en RGB si viene de img_rgb
        else:
            axes[0].imshow(Image.open(query_path))
        axes[0].set_title("Query Image")
        axes[0].axis('off')

        # Imágenes similares
        for i in range(min(top_k, len(similarities))):
            path, score, img = similarities[i]
            axes[i+1].imshow(img)
            axes[i+1].set_title(f"Score: {score:.4f}")
            axes[i+1].axis('off')

    plt.tight_layout()
    plt.show()

    # Limpiar archivo temporal si fue creado
    if isinstance(input_image, np.ndarray) and os.path.exists(temp_path):
        os.remove(temp_path)

    # Devolver los resultados
    return [(path, score) for path, score, _ in similarities[:top_k]]

"""# Usar la función con la región recortada
similar_images = rank_similar_images(crop, top_k=5)
print("\nImágenes más similares del manual:")
for i, (path, score) in enumerate(similar_images, 1):
    print(f"{i}. {os.path.basename(path)}: {score:.4f}")"""