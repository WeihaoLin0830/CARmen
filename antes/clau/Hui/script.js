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
                
                // Importar la explicación desde un archivo Python
                // Realizamos una solicitud al backend para obtener la explicación
                fetch('http://localhost:8000/api/explanation')
                    .then(response => {
                        // Verificamos si la respuesta es exitosa
                        if (!response.ok) {
                            throw new Error('Error al obtener la explicación desde el backend');
                        }
                        return response.json(); // Convertimos la respuesta a JSON
                    })
                    .then(data => {
                        // Actualizamos el contenido de la explicación con los datos recibidos
                        explanationContent.innerHTML = data.response || `
                            <p>No se encontró información para esta parte seleccionada.</p>
                        `;
                    })
                    .catch(error => {
                        // Manejamos errores en caso de que la solicitud falle
                        console.error('Error al obtener la explicación:', error);
                        explanationContent.innerHTML = `
                            <p>Ocurrió un error al obtener la información. Por favor, inténtalo de nuevo más tarde.</p>
                        `;
                    });
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
        
        // Mostrar indicador de carga
        simulatorLoading.style.display = 'block';
        
        // Crear un canvas temporal para el recorte
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Establecer dimensiones del canvas al tamaño del recorte
        canvas.width = boxWidth;
        canvas.height = boxHeight;
        
        // Crear una imagen para el recorte
        const img = new Image();
        img.crossOrigin = 'anonymous';
        
        img.onload = function() {
            // Dibujar solo la parte seleccionada de la imagen en el canvas
            ctx.drawImage(
                img,
                boxLeft, boxTop, // Coordenadas de inicio en la imagen original
                boxWidth, boxHeight, // Tamaño del área a recortar
                0, 0, // Coordenadas de destino en el canvas
                boxWidth, boxHeight // Tamaño en el canvas
            );
            
            // Convertir el canvas a una URL de datos
            const croppedImageUrl = canvas.toDataURL('image/png');
            
            // Actualizar la imagen recortada
            simulatorCroppedImage.src = croppedImageUrl;
            
            // Ocultar indicador de carga
            simulatorLoading.style.display = 'none';
            
            // Mostrar contenedor de explicación
            simulatorExplanationContainer.style.display = 'block';
            
            // Mostrar información del componente basada en la posición
            simulatorExplanationContent.innerHTML = `
                <p><strong>Componente detectado:</strong> ${getComponentName(boxLeft, boxTop)}</p>
                <p>Esta es la información sobre la parte seleccionada del Cupra Tavascan en la simulación 3D.</p>
                <p>Este componente es crucial para el funcionamiento óptimo del vehículo.</p>
                <p>Para más detalles, consulta la sección correspondiente en el manual del propietario o pregunta al asistente virtual.</p>
            `;
        };
        
        // Cargar la imagen actual del simulador
        img.src = simulatorImage.src;
    });

    // Función para determinar qué componente se ha seleccionado (simulación)
    function getComponentName(x, y) {
        // Esta función simula la detección de componentes basada en coordenadas
        // En una implementación real, esto podría conectarse a una API o base de datos
        
        // Zona superior del vehículo
        if (y < 100) {
            return "Techo panorámico";
        }
        // Zona frontal
        else if (x < 150 && y > 100 && y < 200) {
            return "Faros LED adaptativos";
        }
        // Zona central
        else if (x >= 150 && x <= 300 && y > 100 && y < 200) {
            return "Sistema de info-entretenimiento";
        }
        // Zona trasera
        else if (x > 300) {
            return "Luz trasera LED dinámica";
        }
        // Zona inferior
        else if (y >= 200) {
            return "Llantas de aleación de 20 pulgadas";
        }
        // Por defecto
        else {
            return "Carrocería aerodinámica";
        }
    }

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

    // Funcionalidad del chatbot
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSubmitBtn = document.getElementById('chat-submit');
    
    // Función para añadir un nuevo mensaje al chat
    function addMessage(message, isUser = false) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${isUser ? 'user' : 'bot'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messagePara = document.createElement('p');
        messagePara.textContent = message;
        
        messageContent.appendChild(messagePara);
        messageEl.appendChild(messageContent);
        
        // Encontrar el contenedor de mensajes y añadir el mensaje
        const messagesContainer = document.querySelector('.chat-messages');
        messagesContainer.appendChild(messageEl);
        
        // Auto-scroll hacia abajo para mostrar el mensaje más reciente
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return messageEl;
    }
    
    // Función para enviar un mensaje al chatbot y mostrar la respuesta
    function sendToChatbot(userMessage) {
        // Añadir mensaje de usuario al chat
        addMessage(userMessage, true);
        
        // Limpiar el input después de enviar
        chatInput.value = '';
        
        // Mostrar indicador de escritura
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'message bot typing';
        typingIndicator.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        
        // Añadir el indicador de escritura al contenedor de mensajes
        const messagesContainer = document.querySelector('.chat-messages');
        messagesContainer.appendChild(typingIndicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Simular llamada a la API (reemplazar con llamada real a la API)
        fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: userMessage })
        })
        .then(response => {
            // Eliminar indicador de escritura
            messagesContainer.removeChild(typingIndicator);
            
            if (!response.ok) {
                throw new Error('Error en la comunicación con el chatbot');
            }
            return response.json();
        })
        .then(data => {
            // Mostrar respuesta del bot
            addMessage(data.response);
        })
        .catch(error => {
            // Eliminar indicador de escritura
            if (typingIndicator.parentNode) {
                messagesContainer.removeChild(typingIndicator);
            }
            
            // Mostrar mensaje de error
            const errorMsg = 'Lo siento, ha ocurrido un error. Por favor, inténtalo de nuevo más tarde.';
            addMessage(errorMsg);
            console.error('Error:', error);
            
            // Usar una función de respaldo para simular respuestas
            handleChatbotFallback(userMessage);
        });
    }
    
    // Event listeners para entrada de chat
    chatSubmitBtn.addEventListener('click', function() {
        const message = chatInput.value.trim();
        if (message) {
            sendToChatbot(message);
            chatInput.value = '';
        }
    });
    
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const message = chatInput.value.trim();
            if (message) {
                sendToChatbot(message);
                chatInput.value = '';
            }
        }
    });
    
    // Función de respaldo para cuando falla la llamada a la API (para fines de demostración)
    function handleChatbotFallback(userMessage) {
        // Mapeo simple de respuestas para demo
        const responses = {
            'hola': '¡Hola! ¿En qué puedo ayudarte con tu CUPRA Tavascan hoy?',
            'sistema de carga': 'El CUPRA Tavascan cuenta con un sistema de carga rápida de hasta 135 kW que permite cargar del 5% al 80% en aproximadamente 30 minutos en estaciones adecuadas.',
            'mantenimiento': 'El mantenimiento recomendado para tu CUPRA Tavascan es cada 30.000 km o una vez al año. Puedes programar tu cita en cualquier servicio oficial CUPRA.',
            'funciones del volante': 'El volante multifunción del CUPRA Tavascan integra controles para infoentretenimiento, asistentes de conducción y selección de modos de conducción. El botón CUPRA permite cambiar rápidamente entre los modos predefinidos.',
            'modos de conducción': 'El CUPRA Tavascan ofrece varios modos de conducción: Comfort, Sport, CUPRA e Individual. Cada uno modifica parámetros como la respuesta del acelerador, dirección y suspensión adaptativa.'
        };
        
        // Buscar palabras clave en el mensaje del usuario
        let botResponse = 'Lo siento, no tengo información específica sobre eso. ¿Puedo ayudarte con algo más sobre tu CUPRA Tavascan?';
        
        const lowerMessage = userMessage.toLowerCase();
        
        Object.keys(responses).forEach(key => {
            if (lowerMessage.includes(key)) {
                botResponse = responses[key];
            }
        });
        
        // Añadir respuesta del bot al chat después de un retraso para simular "pensamiento"
        setTimeout(() => {
            addMessage(botResponse);
        }, 1000);
    }

    // Función para inicializar y asegurar que el chatbox esté funcionando correctamente
    function initializeChatbox() {
        const chatContainer = document.getElementById('chat-container');
        const chatInput = document.getElementById('chat-input');
        const chatSubmitBtn = document.getElementById('chat-submit');
        const messagesContainer = document.querySelector('.chat-messages');
        
        if (chatContainer && chatInput && chatSubmitBtn) {
            console.log("Chatbox inicializado correctamente");
            
            // Ensure chat container takes full height
            chatContainer.style.display = 'flex';
            chatContainer.style.flexDirection = 'column';
            chatContainer.style.height = '100%';
            
            // Configure the messages container for proper scrolling
            if (messagesContainer) {
                messagesContainer.style.overflowY = 'auto';
                messagesContainer.style.flex = '1';
                
                // Aseguramos que haya suficiente espacio para la barra de entrada
                const chatInputHeight = document.querySelector('.chat-input-container').offsetHeight;
                messagesContainer.style.paddingBottom = (chatInputHeight + 20) + 'px';
                
                // Scroll al último mensaje
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            // Focus the input automatically when the page loads
            setTimeout(() => {
                chatInput.focus();
            }, 500);
            
            // Remove the event that requires clicking on the container first
            // Instead, ensure the input can be focused at any time
            chatInput.addEventListener('click', function(e) {
                // Stop propagation to prevent other click handlers
                e.stopPropagation();
            });
            
            // Add welcome message if no messages exist
            if (document.querySelectorAll('.chat-messages .message').length === 0) {
                addMessage("¡Hola! Soy tu asistente virtual de CUPRA. ¿En qué puedo ayudarte hoy?", false);
            }
        } else {
            console.error("Faltan elementos del chatbox. Verifica que todos los IDs existan en el HTML.");
        }
    }
    
    // Inicializar chatbox después de que todo esté cargado
    window.addEventListener('load', initializeChatbox);
    
    // También enfocamos el input cuando se cambia a la pestaña correspondiente
    document.querySelectorAll('.menu-link').forEach(link => {
        link.addEventListener('click', function() {
            // Cuando se cambia de pestaña, verificar si debemos enfocar el chat
            setTimeout(() => {
                const chatInput = document.getElementById('chat-input');
                if (chatInput && window.getComputedStyle(chatInput).display !== 'none') {
                    chatInput.focus();
                }
            }, 300);
        });
    });
});