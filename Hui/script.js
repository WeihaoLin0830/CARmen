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
    let isNavigating = false; // Variable para controlar si estamos en transición
    
    // Variables para la navegación continua
    let navigationInterval = null;
    const navigationSpeed = 150; // Velocidad de cambio de imágenes en milisegundos

    // Cargar la imagen inicial
    simulatorImage.src = img3dFolder + images[currentImageIndex];

    // Función para cambiar imagen con control de navegación
    function changeImage(direction) {
        // Si ya estamos navegando, ignorar el clic
        if (isNavigating) return;
        
        // Activar el bloqueo de navegación
        isNavigating = true;
        
        // Añadir clase para efecto visual de transición
        simulatorImage.classList.add('transitioning');
        
        // Calcular el nuevo índice
        if (direction === 'prev') {
            currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
        } else {
            currentImageIndex = (currentImageIndex + 1) % images.length;
        }
        
        // Actualizar la imagen
        simulatorImage.src = img3dFolder + images[currentImageIndex];
        
        // Liberar el bloqueo después de un breve tiempo
        setTimeout(() => {
            isNavigating = false;
            simulatorImage.classList.remove('transitioning');
        }, 100); // Reducido para permitir cambios más rápidos cuando se mantiene presionado
    }

    // Función para iniciar la navegación continua
    function startContinuousNavigation(direction) {
        // Primero cambiamos la imagen una vez inmediatamente
        changeImage(direction);
        
        // Luego configuramos el intervalo para cambios continuos
        navigationInterval = setInterval(() => {
            changeImage(direction);
        }, navigationSpeed);
    }

    // Función para detener la navegación continua
    function stopContinuousNavigation() {
        if (navigationInterval) {
            clearInterval(navigationInterval);
            navigationInterval = null;
        }
    }

    // Eventos para navegación continua con el botón anterior
    prevBtn.addEventListener('mousedown', function() {
        startContinuousNavigation('prev');
    });
    
    prevBtn.addEventListener('mouseup', stopContinuousNavigation);
    prevBtn.addEventListener('mouseleave', stopContinuousNavigation);
    
    // Eventos para navegación continua con el botón siguiente
    nextBtn.addEventListener('mousedown', function() {
        startContinuousNavigation('next');
    });
    
    nextBtn.addEventListener('mouseup', stopContinuousNavigation);
    nextBtn.addEventListener('mouseleave', stopContinuousNavigation);

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
                
                // Ocultar las instrucciones cuando se ha subido la imagen
                const instructionsEl = document.querySelector('.instructions');
                if (instructionsEl) {
                    instructionsEl.style.display = 'none';
                }
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
            
            // SIMULACIÓN: Para demostración, usamos un timeout para simular respuesta del backend
            setTimeout(function() {
                // Ocultar indicador de carga
                loading.style.display = 'none';
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
    const simulatorCroppedImage = null; // Anteriormente: document.getElementById('simulator-cropped-image');

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
        
        // Mostrar indicador de carga
        simulatorLoading.style.display = 'block';
        
        // Simulación de procesamiento
        setTimeout(function() {
            // Ocultar indicador de carga
            simulatorLoading.style.display = 'none';
            
            // Alertar al usuario sobre la parte seleccionada
            const boxWidth = parseInt(simulatorSelectionBox.style.width);
            const boxHeight = parseInt(simulatorSelectionBox.style.height);
            const boxLeft = parseInt(simulatorSelectionBox.style.left);
            const boxTop = parseInt(simulatorSelectionBox.style.top);
            
            alert(`Área seleccionada: (${boxLeft}, ${boxTop}) - ${boxWidth}x${boxHeight}px`);
            
            // Reiniciar la selección después de procesar
            simulatorSelectionBox.style.display = 'none';
        }, 1000);
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

    // Funcionalidad del chatbot
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSubmitBtn = document.getElementById('chat-submit');
    
    // Variables para el manual PDF
    const pdfModal = document.getElementById('pdf-modal');
    const pdfContent = document.getElementById('pdf-content');
    const pdfCloseBtn = document.getElementById('pdf-viewer-close');
    const pdfPrevBtn = document.getElementById('pdf-prev');
    const pdfNextBtn = document.getElementById('pdf-next');
    const pdfPageInfo = document.getElementById('pdf-page-info');
    let currentPdfPage = 1;
    let totalPdfPages = 400; // Actualizado para reflejar el número real de páginas del PDF
    const pdfUrl = './manual/cupra_tavascan_manual.pdf'; // Ruta actualizada al PDF real
    
    // Función para añadir un nuevo mensaje al chat
    function addMessage(message, isUser = false, manualPage = null) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${isUser ? 'user' : 'bot'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messagePara = document.createElement('p');
        messagePara.textContent = message;
        
        messageContent.appendChild(messagePara);
        
        // Si hay una referencia a una página del manual, añadir el botón
        if (manualPage !== null && !isUser) {
            const manualBtn = document.createElement('button');
            manualBtn.className = 'manual-ref-btn';
            manualBtn.setAttribute('data-page', manualPage);
            manualBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                </svg>
                Ver página ${manualPage} del manual
            `;
            
            // Evento al hacer clic en el botón del manual
            manualBtn.addEventListener('click', function() {
                openPdfAtPage(manualPage);
            });
            
            messageContent.appendChild(manualBtn);
        }
        
        messageEl.appendChild(messageContent);
        
        // Encontrar el contenedor de mensajes y añadir el mensaje
        const messagesContainer = document.querySelector('.chat-messages');
        messagesContainer.appendChild(messageEl);
        
        // Auto-scroll hacia abajo para mostrar el mensaje más reciente
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return messageEl;
    }
    
    // Inicialización del chatbox con botón del manual
    function initializeChatbox() {
        // Añadir mensaje inicial de bienvenida
        addMessage('¡Hola! Soy tu asistente virtual para el CUPRA Tavascan. ¿En qué puedo ayudarte?', false);
        
        // Añadir botón del manual directamente en la interfaz
        const manualButton = document.createElement('button');
        manualButton.id = 'manual-button';
        manualButton.className = 'manual-main-btn';
        manualButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
            </svg>
            Ver Manual Completo
        `;
        
        // Añadir evento para abrir el manual completo
        manualButton.addEventListener('click', function() {
            openPdfAtPage(1); // Abrir en la primera página
        });
        
        // Agregar el botón al contenedor de chat
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            // Crear un contenedor específico para el botón
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'manual-button-container';
            buttonContainer.appendChild(manualButton);
            
            // Insertar antes del área de entrada de chat
            const chatInputArea = document.querySelector('.chat-input-area');
            if (chatInputArea) {
                chatContainer.insertBefore(buttonContainer, chatInputArea);
            } else {
                chatContainer.appendChild(buttonContainer);
            }
        }
        
        // Configurar el evento para el botón de envío de chat
        chatSubmitBtn.addEventListener('click', function() {
            const message = chatInput.value.trim();
            if (message) {
                sendToChatbot(message);
            }
        });
        
        // También permitir enviar con Enter
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const message = chatInput.value.trim();
                if (message) {
                    sendToChatbot(message);
                }
                e.preventDefault();
            }
        });
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
            // Verificar si la respuesta contiene una referencia a una página del manual
            const manualPage = data.manualPage || null;
            
            // Mostrar respuesta del bot con posible referencia al manual
            addMessage(data.response, false, manualPage);
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
    
    // Función de respaldo para cuando falla la llamada a la API (para fines de demostración)
    function handleChatbotFallback(userMessage) {
        // Mapeo simple de respuestas para demo
        const responses = {
            'hola': {
                text: '¡Hola! ¿En qué puedo ayudarte con tu CUPRA Tavascan hoy?',
                page: null
            },
            'sistema de carga': {
                text: 'El CUPRA Tavascan cuenta con un sistema de carga rápida de hasta 135 kW que permite cargar del 5% al 80% en aproximadamente 30 minutos en estaciones adecuadas.',
                page: 42
            },
            'mantenimiento': {
                text: 'El mantenimiento recomendado para tu CUPRA Tavascan es cada 30.000 km o una vez al año. Puedes programar tu cita en cualquier servicio oficial CUPRA.',
                page: 78
            },
            'funciones del volante': {
                text: 'El volante multifunción del CUPRA Tavascan integra controles para infoentretenimiento, asistentes de conducción y selección de modos de conducción. El botón CUPRA permite cambiar rápidamente entre los modos predefinidos.',
                page: 23
            },
            'modos de conducción': {
                text: 'El CUPRA Tavascan ofrece varios modos de conducción: Comfort, Sport, CUPRA e Individual. Cada uno modifica parámetros como la respuesta del acelerador, dirección y suspensión adaptativa.',
                page: 51
            },
            'manual': {
                text: 'Puedes consultar el manual completo del CUPRA Tavascan desde el botón que aparece debajo. Contiene información detallada sobre todas las características y funcionalidades de tu vehículo.',
                page: 1
            },
            'consumo': {
                text: 'El CUPRA Tavascan tiene un consumo combinado de entre 18-19 kWh/100km según ciclo WLTP. La autonomía en condiciones óptimas alcanza los 520 km con una sola carga.',
                page: 65
            },
            'batería': {
                text: 'La batería del CUPRA Tavascan tiene una capacidad de 77 kWh y cuenta con un sistema de gestión térmica avanzado para optimizar su rendimiento y durabilidad.',
                page: 38
            },
            'garantía': {
                text: 'Tu CUPRA Tavascan cuenta con una garantía de vehículo de 3 años o 100.000 km, y una garantía específica para la batería de 8 años o 160.000 km siempre que se realicen los mantenimientos programados.',
                page: 112
            }
        };
        
        // Buscar palabras clave en el mensaje del usuario
        let botResponse = {
            text: 'Lo siento, no tengo información específica sobre eso. ¿Puedo ayudarte con algo más sobre tu CUPRA Tavascan?',
            page: null
        };
        
        const lowerMessage = userMessage.toLowerCase();
        
        // Verificar si el usuario está pidiendo una página específica del manual
        const pageRegex = /p[áa]gina?\s*(\d+)|manual\s*p[áa]gina?\s*(\d+)|p[áa]g\.*\s*(\d+)/i;
        const pageMatch = lowerMessage.match(pageRegex);
        
        if (pageMatch) {
            // Extraer el número de página de cualquiera de los grupos capturados
            const pageNum = pageMatch[1] || pageMatch[2] || pageMatch[3];
            const pageNumber = parseInt(pageNum, 10);
            
            if (!isNaN(pageNumber) && pageNumber > 0 && pageNumber <= totalPdfPages) {
                botResponse = {
                    text: `Aquí tienes la página ${pageNumber} del manual del CUPRA Tavascan. Puedes hacer clic en el botón para verla.`,
                    page: pageNumber
                };
            } else {
                botResponse = {
                    text: `Lo siento, pero la página ${pageNum} no es válida. El manual tiene ${totalPdfPages} páginas en total. Puedes preguntar por una página específica o ver el manual completo.`,
                    page: 1
                };
            }
        } else {
            // Si no es una petición de página específica, buscar palabras clave
            Object.keys(responses).forEach(key => {
                if (lowerMessage.includes(key)) {
                    botResponse = responses[key];
                }
            });
            
            // Verificar si se menciona el manual en general
            if (lowerMessage.includes('manual') || lowerMessage.includes('instrucciones') || lowerMessage.includes('guía')) {
                if (botResponse.text === 'Lo siento, no tengo información específica sobre eso. ¿Puedo ayudarte con algo más sobre tu CUPRA Tavascan?') {
                    botResponse = {
                        text: 'Puedes consultar el manual completo del CUPRA Tavascan haciendo clic en el botón a continuación. ¿Hay alguna sección específica que te interese?',
                        page: 1
                    };
                }
            }
        }
        
        // Añadir respuesta del bot al chat después de un retraso para simular "pensamiento"
        setTimeout(() => {
            addMessage(botResponse.text, false, botResponse.page);
        }, 1000);
    }

    // Funcionalidad para el visor de PDF del manual
    function openPdfAtPage(pageNumber) {
        // Validar y ajustar el número de página
        currentPdfPage = pageNumber ? parseInt(pageNumber) : 1;
        if (currentPdfPage < 1) currentPdfPage = 1;
        if (currentPdfPage > totalPdfPages) currentPdfPage = totalPdfPages;
        
        // Actualizar el contenedor del PDF
        loadPdfContent();
        
        // Mostrar el modal
        pdfModal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Evitar scroll en el fondo
    }
    
    function loadPdfContent() {
        // Crear el iframe o embed para mostrar el PDF en la página específica
        pdfContent.innerHTML = '';
        
        // Usar un iframe con ruta absoluta para mayor compatibilidad
        const iframe = document.createElement('iframe');
        iframe.src = `${pdfUrl}#page=${currentPdfPage}`;
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        pdfContent.appendChild(iframe);
        
        // Backup en caso de que el iframe no funcione bien con el PDF
        iframe.onerror = function() {
            pdfContent.innerHTML = `
                <embed 
                    src="${pdfUrl}#page=${currentPdfPage}" 
                    type="application/pdf" 
                    width="100%" 
                    height="100%">
                <p>Tu navegador no puede mostrar PDFs. <a href="${pdfUrl}" target="_blank">Descargar PDF</a></p>
            `;
        };
        
        // Actualizar la información de la página
        updatePageInfo();
    }
    
    function updatePageInfo() {
        pdfPageInfo.textContent = `Página ${currentPdfPage} de ${totalPdfPages}`;
    }
    
    // Navegación del PDF
    pdfPrevBtn.addEventListener('click', function() {
        if (currentPdfPage > 1) {
            currentPdfPage--;
            loadPdfContent();
        }
    });
    
    pdfNextBtn.addEventListener('click', function() {
        if (currentPdfPage < totalPdfPages) {
            currentPdfPage++;
            loadPdfContent();
        }
    });
    
    // Cerrar el modal del PDF
    pdfCloseBtn.addEventListener('click', function() {
        pdfModal.classList.remove('active');
        document.body.style.overflow = ''; // Restaurar el scroll
    });
    
    // También cerrar al hacer clic fuera del contenedor
    pdfModal.addEventListener('click', function(e) {
        if (e.target === pdfModal) {
            pdfModal.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
    
    // Cerrar con la tecla Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && pdfModal.classList.contains('active')) {
            pdfModal.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
    
    // Cargar información del PDF al inicio
    function initializePdfViewer() {
        // Asegurarnos de que el PDF existe comprobando si hay respuesta
        fetch(pdfUrl, { method: 'HEAD' })
            .then(response => {
                if (response.ok) {
                    console.log('PDF encontrado y accesible');
                    // Podríamos usar PDF.js para obtener el número real de páginas
                    // Por ahora usamos el valor conocido de 400 páginas
                    totalPdfPages = 400;
                } else {
                    console.error('El PDF no es accesible en la ruta especificada');
                    // Mostrar mensaje de error en la consola
                    alert('Error: No se pudo cargar el manual PDF. Comprueba que el archivo existe en ./manual/cupra_tavascan_manual.pdf');
                }
            })
            .catch(error => {
                console.error('Error al verificar el PDF:', error);
            });
    }

    // Inicializar chatbox después de que todo esté cargado
    window.addEventListener('load', initializeChatbox);
    window.addEventListener('load', initializePdfViewer);
    
    // Optimizar el espacio visual dinámicamente según el tamaño de pantalla
    function optimizeVisualSpace() {
        // Comprobar altura de la ventana
        const windowHeight = window.innerHeight;
        
        // Ajustar containers según altura disponible
        const containers = document.querySelectorAll('.container');
        containers.forEach(container => {
            // En pantallas muy pequeñas, reducir más el padding
            if (windowHeight < 600) {
                container.style.padding = '1rem';
            } else if (windowHeight < 800) {
                container.style.padding = '1.25rem';
            } else {
                container.style.padding = '1.5rem';
            }
        });
        
        // Ajustar visibilidad de las imágenes de áreas seleccionadas (solo para la pestaña home)
        const croppedImages = document.querySelectorAll('#cropped-image');
        if (windowHeight < 700) {
            croppedImages.forEach(img => {
                img.style.display = 'none';
            });
            
            // Ajustar el layout de la explicación
            document.querySelectorAll('.selected-area').forEach(area => {
                area.style.flexDirection = 'column';
                area.style.gap = '0.5rem';
            });
        } else {
            croppedImages.forEach(img => {
                img.style.display = 'block';
            });
            
            document.querySelectorAll('.selected-area').forEach(area => {
                area.style.flexDirection = 'row';
                area.style.gap = '0.8rem';
            });
        }
        
        // Ajustar altura máxima de las imágenes según altura de ventana
        let maxImageHeight = 380; // valor predeterminado
        
        if (windowHeight < 600) {
            maxImageHeight = 280;
        } else if (windowHeight < 700) {
            maxImageHeight = 320;
        } else if (windowHeight < 800) {
            maxImageHeight = 350;
        }
        
        // Aplicar la altura máxima a los contenedores de imágenes
        document.querySelectorAll('.image-container, #image-container').forEach(container => {
            container.style.maxHeight = maxImageHeight + 'px';
        });
        
        document.querySelectorAll('#uploaded-image, #simulator-image').forEach(img => {
            img.style.maxHeight = maxImageHeight + 'px';
        });
    }

    // Ejecutar la optimización al cargar y cuando se redimensione la ventana
    window.addEventListener('load', optimizeVisualSpace);
    window.addEventListener('resize', optimizeVisualSpace);
    
    // También ejecutar la optimización cuando se cambie de pestaña
    document.querySelectorAll('.menu-link').forEach(link => {
        link.addEventListener('click', function() {
            setTimeout(optimizeVisualSpace, 100);
        });
    });
    
    // Nueva sección: Funcionalidad para los botones de New Features
    const volanteBtn = document.getElementById('volante-btn');
    const seatbeltBtn = document.getElementById('seatbelt-btn');
    const featureImage = document.getElementById('feature-image');
    const featureDescription = document.getElementById('feature-description');
    
    // Función para mostrar imagen de característica
    function showFeatureImage(imageSrc, description) {
        // Primero ocultamos la imagen actual con animación
        featureImage.classList.remove('visible');
        featureDescription.classList.remove('visible');
        
        // Después de un breve delay, cambiamos la imagen y la mostramos
        setTimeout(() => {
            featureImage.src = imageSrc;
            featureImage.style.display = 'inline-block';
            featureDescription.textContent = description;
            
            // Dar tiempo al navegador para cargar la imagen
            setTimeout(() => {
                featureImage.classList.add('visible');
                featureDescription.classList.add('visible');
            }, 50);
        }, 300);
    }
    
    // Configurar eventos de los botones
    volanteBtn.addEventListener('click', function() {
        showFeatureImage('volante.jpg', 'El nuevo volante multifunción del CUPRA Tavascan incorpora controles táctiles de última generación y un diseño ergonómico que mejora la experiencia de conducción.');
    });
    
    seatbeltBtn.addEventListener('click', function() {
        showFeatureImage('seatbelt.jpg', 'El innovador sistema SeatBelt ofrece protección adicional en colisiones laterales, desplegándose en milisegundos para proteger a los ocupantes.');
    });
});