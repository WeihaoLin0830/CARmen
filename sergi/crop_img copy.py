import numpy as np
import cv2
import os

def crop_image(image, box):
    """
    Recorta una imagen según las coordenadas de una caja.
    
    Args:
        image: Imagen de entrada (numpy array)
        box: Array numpy con las coordenadas [x0, y0, x1, y1]
    
    Returns:
        Imagen recortada
    """
    # Extraer coordenadas
    x0, y0, x1, y1 = box[0]
    
    # Asegurar que las coordenadas estén dentro de los límites de la imagen
    height, width = image.shape[:2]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(width, x1)
    y1 = min(height, y1)
    
    # Recortar la imagen
    cropped_image = image[y0:y1, x0:x1]
    
    return cropped_image

# Variables globales para la selección del recorte
drawing = False  # Indica si se está dibujando el rectángulo
ix, iy = -1, -1  # Punto inicial
fx, fy = -1, -1  # Punto final
selection_done = False  # Indica si la selección está completa

# Función de callback para eventos del ratón
def draw_rectangle(event, x, y, flags, param):
    global ix, iy, fx, fy, drawing, selection_done, img_copy
    
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        selection_done = False
        ix, iy = x, y
        fx, fy = x, y
        img_copy = image.copy()
        
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_copy = image.copy()
            cv2.rectangle(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)
            fx, fy = x, y
            
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        selection_done = True
        cv2.rectangle(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)
        fx, fy = x, y

# Obtener la ruta del script actual
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construir la ruta relativa desde el script
image_path = os.path.join(script_dir, "..", "..", "cupra_frames", "1.png")
image = cv2.imread(image_path)

if image is None:
    print(f"No se pudo cargar la imagen: {image_path}")
    exit()

img_copy = image.copy()

# Crear ventana y asignar función de callback
cv2.namedWindow('Selecciona área a recortar')
cv2.setMouseCallback('Selecciona área a recortar', draw_rectangle)

print("Instrucciones:")
print("1. Haz clic y arrastra para seleccionar el área a recortar")
print("2. Presiona 'c' para confirmar el recorte")
print("3. Presiona 'r' para reiniciar la selección")
print("4. Presiona 'ESC' para salir")

while True:
    cv2.imshow('Selecciona área a recortar', img_copy)
    key = cv2.waitKey(1) & 0xFF
    
    # Salir con ESC
    if key == 27:
        break
    
    # Confirmar recorte con 'c'
    elif key == ord('c') and selection_done:
        # Ordenar coordenadas para asegurar que x0<x1 y y0<y1
        x0, x1 = min(ix, fx), max(ix, fx)
        y0, y1 = min(iy, fy), max(iy, fy)
        
        # Crear box y recortar la imagen
        box = np.array([[x0, y0, x1, y1]], dtype=np.int32)
        cropped = crop_image(image, box)
        
        # Mostrar resultado
        cv2.imshow('Imagen recortada', cropped)
        print(f"Coordenadas del recorte: x0={x0}, y0={y0}, x1={x1}, y1={y1}")
        
    # Reiniciar selección con 'r'
    elif key == ord('r'):
        img_copy = image.copy()
        selection_done = False

cv2.destroyAllWindows()