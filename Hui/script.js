document.addEventListener('DOMContentLoaded', function() {
    // Elementos DOM
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const uploadedImage = document.getElementById('uploaded-image');
    const imageWorkspace = document.getElementById('image-workspace');
    const selectionOverlay = document.getElementById('selection-overlay');
    const selectionBox = document.getElementById('selection-box');
    const resetBtn = document.getElementById('reset-btn');
    const submitBtn = document.getElementById('submit-btn');
    const loading = document.getElementById('loading');
    const explanationContainer = document.getElementById('explanation-container');
    const explanationContent = document.getElementById('explanation-content');
    const croppedImage = document.getElementById('cropped-image');
    
    // Variables para la selección
    let isSelecting = false;
    let startX, startY, currentX, currentY;
    let imageData = null;
    
    // Evento para abrir el explorador de archivos
    browseBtn.addEventListener('click', function() {
        fileInput.click();
    });
    
    // Cuando se selecciona un archivo
    fileInput.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(event) {
                uploadedImage.src = event.target.result;
                imageData = event.target.result;
                imageWorkspace.style.display = 'flex';
                explanationContainer.style.display = 'none';
            };
            
            reader.readAsDataURL(e.target.files[0]);
        }
    });
    
    // Eventos para la selección con el mouse
    selectionOverlay.addEventListener('mousedown', function(e) {
        isSelecting = true;
        
        // Calcula la posición relativa al elemento de la imagen
        const rect = selectionOverlay.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
        
        selectionBox.style.display = 'block';
        selectionBox.style.left = startX + 'px';
        selectionBox.style.top = startY + 'px';
        selectionBox.style.width = '0px';
        selectionBox.style.height = '0px';
    });
    
    selectionOverlay.addEventListener('mousemove', function(e) {
        if (!isSelecting) return;
        
        // Calcula la posición relativa al elemento de la imagen
        const rect = selectionOverlay.getBoundingClientRect();
        currentX = e.clientX - rect.left;
        currentY = e.clientY - rect.top;
        
        // Calcular dimensiones y posición del recuadro
        const width = Math.abs(currentX - startX);
        const height = Math.abs(currentY - startY);
        const left = Math.min(startX, currentX);
        const top = Math.min(startY, currentY);
        
        selectionBox.style.width = width + 'px';
        selectionBox.style.height = height + 'px';
        selectionBox.style.left = left + 'px';
        selectionBox.style.top = top + 'px';
    });
    
    // Finalizar selección cuando se suelta el mouse
    document.addEventListener('mouseup', function() {
        if (isSelecting) {
            isSelecting = false;
        }
    });
    
    // Reiniciar selección
    resetBtn.addEventListener('click', function() {
        selectionBox.style.display = 'none';
        explanationContainer.style.display = 'none';
    });
    
    // Enviar solicitud al backend
    submitBtn.addEventListener('click', function() {
        if (selectionBox.style.display === 'none') {
            alert('Por favor, selecciona una parte de la imagen primero');
            return;
        }
        
        // Obtener coordenadas de selección
        const boxLeft = parseInt(selectionBox.style.left);
        const boxTop = parseInt(selectionBox.style.top);
        const boxWidth = parseInt(selectionBox.style.width);
        const boxHeight = parseInt(selectionBox.style.height);
        
        // Mostrar indicador de carga
        loading.style.display = 'block';
        
        // Crear un canvas para recortar la imagen
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Crear una imagen para cargar la original
        const img = new Image();
        img.onload = function() {
            // Configurar el canvas con el tamaño de la selección
            canvas.width = boxWidth;
            canvas.height = boxHeight;
            
            // Recortar la imagen
            ctx.drawImage(img, boxLeft, boxTop, boxWidth, boxHeight, 0, 0, boxWidth, boxHeight);
            
            // Obtener la imagen recortada como base64
            const croppedImageData = canvas.toDataURL('image/jpeg');
            
            // Mostrar la imagen recortada
            croppedImage.src = croppedImageData;
            
            // SIMULACIÓN: En una implementación real, aquí se enviaría la solicitud al backend
            // Descomentar y modificar el siguiente bloque para la implementación real
            
            /*
            fetch('TU_URL_DE_BACKEND_AQUI', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    fullImage: imageData,
                    croppedImage: croppedImageData,
                    selection: {
                        x: boxLeft,
                        y: boxTop,
                        width: boxWidth,
                        height: boxHeight
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                // Ocultar indicador de carga
                loading.style.display = 'none';
                
                // Mostrar explicación recibida del backend
                explanationContainer.style.display = 'block';
                explanationContent.innerHTML = data.explanation || 'No se encontró información para esta parte.';
            })
            .catch(error => {
                loading.style.display = 'none';
                alert('Error al procesar la imagen. Por favor, intenta de nuevo.');
                console.error('Error:', error);
            });
            */
            
            // SIMULACIÓN: Para demostración, usamos un timeout para simular respuesta del backend
            setTimeout(function() {
                // Ocultar indicador de carga
                loading.style.display = 'none';
                
                // Mostrar explicación
                explanationContainer.style.display = 'block';
                
                // Simular una respuesta del backend
                explanationContent.innerHTML = `
                    <p>Esta es la información sobre la parte seleccionada del Cupra Tavascan.</p>
                    <p>En una implementación real, aquí aparecería la explicación enviada por el backend después de analizar las imágenes.</p>
                    <p>La explicación incluiría detalles sobre la funcionalidad, uso correcto y recomendaciones para esta parte específica del vehículo.</p>
                `;
            }, 1500);
        };
        
        img.src = imageData;
    });
});