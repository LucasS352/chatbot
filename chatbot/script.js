// File: script.js - VERSÃO FINAL COM LÓGICA DE TOKEN
document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const modalCaption = document.getElementById('modalCaption');
    const closeModalButton = document.getElementById('closeModalButton');

    // --- LÓGICA PARA OBTER O TOKEN DA URL ---
    let clientToken = null;
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');

    if (tokenFromUrl && tokenFromUrl.trim() !== '') {
        clientToken = tokenFromUrl.trim();
        console.log(`Token de cliente encontrado na URL: ${clientToken}`);
    } else {
        console.error("Token de cliente não encontrado na URL. O chat não funcionará.");
        addMessage('bot', 'ERRO: Token de acesso não fornecido na URL. Não é possível iniciar o chat.');
        // Desabilitar a área de input se não houver token
        userInput.disabled = true;
        sendButton.disabled = true;
        userInput.placeholder = "Acesso negado. Forneça um token na URL.";
    }
    // --- FIM DA LÓGICA DE TOKEN ---

    function addMessage(sender, text, imageUrls = []) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        if (text) {
            const textElement = document.createElement('p');
            textElement.textContent = text;
            messageElement.appendChild(textElement);
        }
        if (imageUrls && imageUrls.length > 0) {
            const imagesContainer = document.createElement('div');
            imagesContainer.classList.add('message-images');
            imageUrls.forEach(url => {
                const imgElement = document.createElement('img');
                imgElement.src = url;
                imgElement.alt = "Imagem da resposta do bot";
                imgElement.onclick = function() {
                    modal.style.display = "flex";
                    modalImg.src = this.src;
                    modalCaption.textContent = this.alt;
                }
                imagesContainer.appendChild(imgElement);
            });
            messageElement.appendChild(imagesContainer);
        }
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function closeModal() {
        modal.style.display = "none";
    }

    closeModalButton.onclick = closeModal;
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeModal();
        }
    }

    async function sendMessage() {
        const question = userInput.value.trim();
        if (question === '' || !clientToken) {
            if (!clientToken) {
                console.error("Tentativa de enviar mensagem sem um token de cliente válido.");
            }
            return;
        }

        addMessage('user', question);
        userInput.value = '';
        userInput.disabled = true;
        sendButton.disabled = true;

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // Corpo da requisição corrigido para enviar o token
                body: JSON.stringify({ 
                    token: clientToken, 
                    question: question 
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Erro da API:', errorData);
                addMessage('bot', `Erro do servidor: ${errorData.detail || 'Erro desconhecido'}`);
                throw new Error(`Erro na API: ${response.status}`);
            }

            const data = await response.json();
            addMessage('bot', data.response, data.images);

        } catch (error) {
            console.error('Erro de comunicação:', error);
            addMessage('bot', 'Falha na comunicação com o servidor.');
        } finally {
            userInput.disabled = false;
            sendButton.disabled = false;
            userInput.focus();
        }
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    if (clientToken) {
        userInput.focus();
    }
});