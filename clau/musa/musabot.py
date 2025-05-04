import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import base64

# ⚠️ Reemplaza esto con tu clave real de API
API_KEY = "4abJigJ5xBlkZA4bDx6F"
WORKSPACE = "hackupc-70ysk"
WORKFLOW_ID = "small-object-detection-sahi-3"
IMAGE_PATH = os.path.join("clau", "imagenes", "cap5.png")  # Evita usar "\" en rutas
# IMAGE_PATH = os.path.join("clau", "imagenes", "cap15.png")  # Evita usar "\" en rutas

def extract_predictions(result):
    """Extrae predicciones del resultado, sin importar la estructura anidada"""
    if "predictions" in result:
        if isinstance(result["predictions"], list):
            if all(isinstance(p, dict) and "x" in p and "y" in p for p in result["predictions"]):
                return result["predictions"]
            for item in result["predictions"]:
                if isinstance(item, dict) and "predictions" in item:
                    if isinstance(item["predictions"], dict) and "predictions" in item["predictions"]:
                        return item["predictions"]["predictions"]
                    elif isinstance(item["predictions"], list):
                        return item["predictions"]
    if "result" in result:
        return extract_predictions(result["result"])
    return find_predictions_recursively(result)

def find_predictions_recursively(data, max_depth=5, current_depth=0):
    """Búsqueda recursiva de predicciones en estructuras anidadas"""
    if current_depth > max_depth:
        return []
    if isinstance(data, dict):
        if "predictions" in data:
            preds = data["predictions"]
            if isinstance(preds, list) and all("x" in p and "y" in p for p in preds):
                return preds
            elif isinstance(preds, dict) and "predictions" in preds:
                return preds["predictions"]
        for value in data.values():
            result = find_predictions_recursively(value, max_depth, current_depth + 1)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_predictions_recursively(item, max_depth, current_depth + 1)
            if result:
                return result
    return []

try:
    # Obtener ruta absoluta de la imagen
    abs_image_path = os.path.abspath(IMAGE_PATH)

    # Codificar la imagen a base64
    with open(abs_image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Crear el payload para la API
    payload = {
        "api_key": API_KEY,
        "inputs": {
            "image": {
                "type": "base64",
                "value": image_data
            }
        }
    }

    url = f"https://serverless.roboflow.com/infer/workflows/{WORKSPACE}/{WORKFLOW_ID}"
    headers = {"Content-Type": "application/json"}

    print(f"Enviando solicitud a {url}...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()

        # Cargar imagen en modo RGBA para permitir transparencia
        img = Image.open(abs_image_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()  # Fuente básica por compatibilidad

        # Dimensiones reales de la imagen
        img_width, img_height = img.size
        print(f"Dimensiones reales: {img_width}x{img_height}")

        # Dimensiones según la API (por si se deben escalar)
        api_img = result.get("predictions", {}).get("image", {})
        api_width = api_img.get("width", img_width)
        api_height = api_img.get("height", img_height)
        print(f"Dimensiones API: {api_width}x{api_height}")

        scale_x = img_width / api_width
        scale_y = img_height / api_height

        # Obtener predicciones
        predictions = extract_predictions(result)
        print(f"Objetos detectados: {len(predictions)}")

        if not predictions:
            print("⚠️ No se detectaron objetos en la imagen.")
        
        for prediction in predictions:
            print("Predicción:", prediction)  # DEBUG
            x = prediction["x"] * scale_x
            y = prediction["y"] * scale_y
            w = prediction["width"] * scale_x
            h = prediction["height"] * scale_y
            label = prediction["class"]
            conf = prediction.get("confidence", 0.0)

            x0 = x - w / 2
            y0 = y - h / 2
            x1 = x + w / 2
            y1 = y + h / 2

            # Dibujar el recuadro
            draw.rectangle([x0, y0, x1, y1], outline="red", width=3)

            # Dibujar el fondo del texto (sin transparencia en RGBA)
            draw.rectangle([x0, y0 - 20, x0 + 110, y0], fill=(255, 0, 0, 255))
            draw.text((x0 + 2, y0 - 18), f"{label} ({conf:.2f})", fill="white", font=font)

        # Guardar la imagen modificada
        output_path = os.path.join(os.path.dirname(abs_image_path), "output_detection.png")
        img.save(output_path)
        print(f"✅ Imagen guardada con recuadros en: {output_path}")

        # Mostrar la imagen convertida a RGB
        img.convert("RGB").show()

    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

except Exception as e:
    print(f"❌ Error general: {e}")
