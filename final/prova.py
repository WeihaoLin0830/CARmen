# Import libraries at the beginning
import json
import sys
import os
from chatbot_text import get_response_json
import re
import numpy as np
import cv2
import time
from crop_img_bo_retrieve import DashboardImageProcessor, ImageChatSession, _rerank_chunks, retrieve_context
from similarity_img import rank_similar_images

# Global variables for pre-loaded resources
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
content_dir = os.path.join(parent_dir, "extracted_content_manual")

# Pre-initialize all heavy resources
print("Inicializando recursos...")
start_time = time.time()

try:
    # Initialize processor
    processor = DashboardImageProcessor()

    # Setup ChromaDB
    text_col, model_text = processor.setup_chromadb(content_dir)

    # Load chunks for retrieval
    chunks = processor.load_chunks(content_dir)

    # Make content_dir available to imported functions
    sys.modules['crop_img_bo_retrieve'].content_dir = content_dir

    # Create chat session
    chat_session = ImageChatSession()

    # Initialize chatbot
    chatbot = get_response_json()

    print(f"Recursos cargados correctamente en {time.time() - start_time:.2f} segundos")
    resources_loaded = True

except Exception as e:
    print(f"Error al cargar recursos: {str(e)}")
    resources_loaded = False

def main():
    print("\n=== PDF Chatbot ===")
    print("Haz una pregunta sobre el manual Cupra Tavascan:")

    # Get single question from user
    question = input("> ")

    if question.strip():
        print("\nProcesando tu pregunta...")

        response_text = chatbot.get_response(question, top_k=3)

        try:
            response_clean = re.sub(r'```json', '', response_text)
            response_clean = re.sub(r'```', '', response_clean)
            response = json.loads(response_clean)

        except json.JSONDecodeError:
            # Return a fallback JSON if parsing fails
            response = {
                "answer": response_text,
                "page_numbers": [],
                "figure_numbers": []
            }

        # Display the answer
        print("\nRespuesta:")
        print(response["answer"])

        # Display page references if available
        if response["page_numbers"]:
            print("\nPáginas relevantes:", ", ".join(map(str, response["page_numbers"])))

        # Display figure references if available
        if response["figure_numbers"]:
            print("Figuras relevantes:", ", ".join(map(str, response["figure_numbers"])))
    else:
        print("No has introducido ninguna pregunta.")

def image():
    """
    Function to handle image input and output.
    Uses pre-loaded resources for instant response.
    """
    if not resources_loaded:
        return {"answer": "Error: Los recursos no se han cargado correctamente",
                "page_numbers": [], "figure_numbers": []}

    print("\n=== Dashboard Component Identifier ===")

    # Define path to the image with absolute path to avoid errors
    image_path = os.path.join(parent_dir, "..", "cupra_frames", "1.png")
    print(f"Loading image from: {image_path}")

    # Define the coordinates of the box [x0, y0, x1, y1]
    box = np.array([[497, 245, 700, 351]], dtype=np.int32)

    print("\nAnalizando componente del dashboard...")

    try:
        start_time = time.time()

        # Get image description - using pre-loaded processor
        description = processor.get_image_description(image_path, box)

        # Use retrieve_context with pre-loaded resources
        image_paths_list, image_contexts = retrieve_context(
            query=description["description"],
            top_k=20,
            collection=text_col,
            chunks=chunks
        )

        # Get cropped image - check if image exists first
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image from {image_path}")

        cropped = processor.crop_image(image, box)

        # Rank similar images
        scores = rank_similar_images(cropped, top_k=3, image_paths_list=image_paths_list)

        # Extract page numbers from image contexts
        top_pages = list(set([image_contexts[img[0]][0] for img in scores if img[0] in image_contexts]))

        # Collect chunks from top pages using pre-loaded chunks
        all_chunks_from_pages = [
            chunk for chunk in chunks if chunk["start_page"] in top_pages
        ]

        # Re-rank chunks based on description
        reranked_chunks = _rerank_chunks(all_chunks_from_pages, description["description"], top_k=3)

        # Generate JSON response using pre-loaded chat session
        json_response = chat_session.generate_json_response(
            description["description"],
            reranked_chunks,
            image_contexts,
            scores
        )

        print(f"\nRespuesta generada en {time.time() - start_time:.2f} segundos")
        print("\nComponente identificado!")
        print("\nInformación del componente:")
        print(json_response["answer"])

        if json_response["page_numbers"]:
            print("\nPáginas relevantes:", ", ".join(map(str, json_response["page_numbers"])))

        if json_response["figure_numbers"]:
            print("Figuras relevantes:", ", ".join(map(str, json_response["figure_numbers"])))

        return json_response

    except Exception as e:
        print(f"Error: {e}")
        return {
            "answer": f"Error procesando imagen: {str(e)}",
            "page_numbers": [],
            "figure_numbers": []
        }

if __name__ == "__main__":
    if resources_loaded:
        image()
    else:
        print("No se puede ejecutar la función debido a errores en la carga de recursos")

