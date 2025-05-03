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

    // Variables para navegación y zoom
    const simulatorImage = document.getElementById('simulator-image');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const img3dFolder = './cupra_frames/';
    const images = Array.from({ length: 93 }, (_, i) => `${i + 1}.png`); 
    let currentImageIndex = 0;
    let zoomLevel = 1;

    // Cambiar imagen al hacer clic en las flechas
    prevBtn.addEventListener('click', function() {
        // Cambiar a la imagen anterior (girar a la izquierda)
        currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
        simulatorImage.src = img3dFolder + images[currentImageIndex];
    });

    nextBtn.addEventListener('click', function() {
        // Cambiar a la imagen siguiente (girar a la derecha)
        currentImageIndex = (currentImageIndex + 1) % images.length;
        simulatorImage.src = img3dFolder + images[currentImageIndex];
    });

    // Funcionalidad de zoom
    zoomInBtn.addEventListener('click', function() {
        zoomLevel += 0.2;
        simulatorImage.style.transform = `scale(${zoomLevel})`;
    });

    zoomOutBtn.addEventListener('click', function() {
        zoomLevel = Math.max(1, zoomLevel - 0.2);
        simulatorImage.style.transform = `scale(${zoomLevel})`;
    });
    
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
        console.log(`Coordenadas de selección: ${boxLeft}, ${boxTop}, ${boxWidth}, ${boxHeight}`);

        // Ajustar las coordenadas según la relación entre el tamaño mostrado y el tamaño original
        const scaleX = uploadedImage.naturalWidth / uploadedImage.clientWidth;
        const scaleY = uploadedImage.naturalHeight / uploadedImage.clientHeight;

        const adjustedBoxLeft = boxLeft * scaleX;
        const adjustedBoxTop = boxTop * scaleY;
        const adjustedBoxWidth = boxWidth * scaleX;
        const adjustedBoxHeight = boxHeight * scaleY;
        console.log(`Coordenadas ajustadas: ${adjustedBoxLeft}, ${adjustedBoxTop}, ${adjustedBoxWidth}, ${adjustedBoxHeight}`);
        
        // Mostrar indicador de carga
        loading.style.display = 'block';
        
        // Crear un canvas para recortar la imagen
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        // Crear una imagen para cargar la original
        const img = new Image();
        img.crossOrigin = 'anonymous'; // Ensure cross-origin requests are allowed
        img.onload = function() {
            if (!img.complete || img.naturalWidth === 0) {
                console.error('Failed to load image. Ensure the image source allows cross-origin requests.');
                alert('Error: Unable to process the image due to cross-origin restrictions.');
                loading.style.display = 'none';
                return;
            }
            // Configurar el canvas con el tamaño de la selección
            canvas.width = boxWidth;
            canvas.height = boxHeight;
            
            // Recortar la imagen
            ctx.drawImage(img, adjustedBoxLeft, adjustedBoxTop, adjustedBoxWidth, adjustedBoxHeight, 0, 0, boxWidth, boxHeight);
            
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

    const video = document.getElementById('background-video');
    video.currentTime = 6; // Comienza desde el segundo 6

    // Lógica para cambiar entre pestañas
    const menuLinks = document.querySelectorAll('.menu-link');
    const tabContents = document.querySelectorAll('.tab-content');

    menuLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            // Quitar la clase 'active' de todos los enlaces y pestañas
            menuLinks.forEach(link => link.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));

            // Añadir la clase 'active' al enlace y pestaña seleccionados
            this.classList.add('active');
            const target = document.querySelector(this.getAttribute('href'));
            target.classList.add('active');
        });
    });

    // Variables para la selección en el simulador
    const simulatorSelectionOverlay = document.getElementById('simulator-selection-overlay');
    const simulatorSelectionBox = document.getElementById('simulator-selection-box');
    const simulatorSubmitBtn = document.getElementById('simulator-submit-btn');
    const simulatorResetBtn = document.getElementById('simulator-reset-btn');
    const simulatorLoading = document.getElementById('simulator-loading');
    const simulatorExplanationContainer = document.getElementById('simulator-explanation-container');
    const simulatorExplanationContent = document.getElementById('simulator-explanation-content');
    const simulatorCroppedImage = document.getElementById('simulator-cropped-image');

    startX = 0;
    startY = 0;
    isSelecting = false;

    // Mejorar la estabilidad del recuadro de selección en el simulador
    simulatorSelectionOverlay.addEventListener('mousedown', function (e) {
        isSelecting = true;
        
        // Usar el mismo enfoque que en la selección de la imagen subida
        const rect = simulatorSelectionOverlay.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
        
        simulatorSelectionBox.style.display = 'block';
        simulatorSelectionBox.style.left = startX + 'px';
        simulatorSelectionBox.style.top = startY + 'px';
        simulatorSelectionBox.style.width = '0px';
        simulatorSelectionBox.style.height = '0px';
    });

    simulatorSelectionOverlay.addEventListener('mousemove', function (e) {
        if (!isSelecting) return;
        
        // Usar el mismo enfoque que en la selección de la imagen subida
        const rect = simulatorSelectionOverlay.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        // Calcular dimensiones y posición del recuadro
        const width = Math.abs(currentX - startX);
        const height = Math.abs(currentY - startY);
        const left = Math.min(startX, currentX);
        const top = Math.min(startY, currentY);
        
        simulatorSelectionBox.style.width = width + 'px';
        simulatorSelectionBox.style.height = height + 'px';
        simulatorSelectionBox.style.left = left + 'px';
        simulatorSelectionBox.style.top = top + 'px';
    });

    // Finalizar selección
    document.addEventListener('mouseup', function () {
        if (isSelecting) {
            isSelecting = false;
            
            // Validar tamaño mínimo para evitar selecciones accidentales
            const boxWidth = parseInt(simulatorSelectionBox.style.width);
            const boxHeight = parseInt(simulatorSelectionBox.style.height);
            
            if (boxWidth < 5 || boxHeight < 5) {
                simulatorSelectionBox.style.display = 'none'; // Ocultar si es muy pequeño
            }
        }
    });

    // Reiniciar selección
    simulatorResetBtn.addEventListener('click', function () {
        simulatorSelectionBox.style.display = 'none';
    });

    // Procesar selección en el simulador
    simulatorSubmitBtn.addEventListener('click', function() {
        if (simulatorSelectionBox.style.display === 'none') {
            alert('Por favor, selecciona una parte de la imagen primero');
            return;
        }

        // Obtener las dimensiones y posición de la selección
        const boxWidth = parseInt(simulatorSelectionBox.style.width);
        const boxHeight = parseInt(simulatorSelectionBox.style.height);
        const boxLeft = parseInt(simulatorSelectionBox.style.left);
        const boxTop = parseInt(simulatorSelectionBox.style.top);
        
        // Verificar que la selección tenga un tamaño mínimo
        if (boxWidth < 10 || boxHeight < 10) {
            alert('Por favor, haz una selección más grande');
            return;
        }
        
        // Crear un canvas temporal para el recorte
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Establecer dimensiones del canvas al tamaño del recorte
        canvas.width = boxWidth;
        canvas.height = boxHeight;
        
        // Dibujar solo la parte seleccionada de la imagen en el canvas
        ctx.drawImage(
            simulatorImage,
            boxLeft, boxTop, // Coordenadas de inicio en la imagen original
            boxWidth, boxHeight, // Tamaño del área a recortar
            0, 0, // Coordenadas de destino en el canvas
            boxWidth, boxHeight // Tamaño en el canvas
        );
        
        // Convertir el canvas a una URL de datos
        const croppedImageUrl = canvas.toDataURL('image/png');
        
        // Mostrar explicación
        simulatorExplanationContainer.style.display = 'block';
        simulatorExplanationContent.innerHTML = `
            <p>Esta es la información sobre la parte seleccionada del Cupra Tavascan en la simulación 3D.</p>
            <p>En una implementación real, aquí aparecería la explicación enviada por el backend después de analizar la imagen recortada.</p>
        `;
        
        // Mostrar la imagen recortada
        simulatorCroppedImage.src = croppedImageUrl;
        simulatorCroppedImage.style.display = 'block';
    });

    const signupForm = document.getElementById('signup-form');
    const carModelSelect = document.getElementById('car-model');
    const errorMessage = document.getElementById('error-message');
    const signupPage = document.getElementById('signup');
    const mainPage = document.querySelector('main');
    const menu = document.getElementById('menu'); // Menú de navegación

    // Ocultar el menú y la página principal inicialmente
    signupPage.style.display = 'block';
    mainPage.style.display = 'none';
    menu.style.display = 'none';

    // Manejar el envío del formulario
    signupForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const selectedModel = carModelSelect.value;

        if (selectedModel === 'CUPRA TAVASCAN') {
            // Mostrar la página principal si el modelo es compatible
            signupPage.style.display = 'none';
            mainPage.style.display = 'block';
            menu.style.display = 'flex'; // Mostrar el menú

            // Guardar el estado de registro en localStorage
            localStorage.setItem('isRegistered', 'true');

            // Eliminar la pestaña de registro del menú
            const signupTab = document.querySelector('a[href="#signup"]');
            if (signupTab) {
                signupTab.parentElement.remove(); // Elimina el elemento <li> del menú
            }
        } else {
            // Mostrar mensaje de error si el modelo no es compatible
            errorMessage.style.display = 'block';
        }
    });
});