# Cupra Tavascan - Asistente Digital

Este proyecto implementa una interfaz web interactiva para la digitalización del manual del Cupra Tavascan. Permite a los usuarios subir imágenes del vehículo, seleccionar partes específicas y recibir información detallada sobre esas partes.

## Características

- Interfaz con el estilo de marca de Cupra
- Subida de imágenes mediante un botón de exploración
- Selección de áreas específicas de la imagen mediante un recuadro
- Recorte automático de la parte seleccionada
- Preparación de datos para envío al backend
- Visualización de la explicación recibida

## Estructura de archivos

- `index.html`: Estructura principal de la página web
- `styles.css`: Estilos y diseño visual con los colores corporativos de Cupra
- `script.js`: Funcionalidades de interacción y procesamiento de imágenes
- `cupra-logo.png`: Logo de la marca (debes añadir este archivo)

## Instalación

1. Descarga todos los archivos en una carpeta
2. Añade el logo de Cupra (un archivo de imagen llamado `cupra-logo.png`)
3. Abre el archivo `index.html` en un navegador web

## Configuración del backend

Para conectar esta interfaz con tu backend, sigue estos pasos:

1. Abre el archivo `script.js`
2. Busca el bloque de código comentado que contiene la función `fetch`
3. Descomenta el bloque
4. Reemplaza `'TU_URL_DE_BACKEND_AQUI'` con la URL de tu API
5. Ajusta el formato de los datos enviados según sea necesario para tu backend

## Formato de datos enviados al backend

La aplicación envía un objeto JSON con la siguiente estructura:

```json
{
  "fullImage": "data:image/jpeg;base64,/9j...", // Imagen completa en base64
  "croppedImage": "data:image/jpeg;base64,/9j...", // Imagen recortada en base64
  "selection": {
    "x": 100, // Posición X del recuadro (desde la esquina superior izquierda)
    "y": 150, // Posición Y del recuadro
    "width": 200, // Ancho del recuadro
    "height": 150 // Alto del recuadro
  }
}
```

## Formato de respuesta esperado del backend

La aplicación espera recibir un objeto JSON con al menos la siguiente propiedad:

```json
{
  "explanation": "<p>Texto HTML con la explicación sobre la parte seleccionada</p>"
}
```

## Personalización

- Los colores de la marca Cupra están definidos como variables CSS en `styles.css`
- Para modificar el diseño, ajusta las propiedades en el archivo CSS
- El contenido de las instrucciones puede ser modificado en el archivo HTML

## Compatibilidad

Esta aplicación es compatible con navegadores modernos como:
- Chrome
- Firefox
- Safari
- Edge

## Notas de implementación

- La selección del área funciona con eventos de mouse
- Se utiliza Canvas API para recortar la imagen
- Las imágenes se procesan como base64 para facilitar la transmisión
- La aplicación incluye una simulación de la respuesta del backend