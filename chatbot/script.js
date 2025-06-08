// File: script.js - VERSÃO COM BOTÕES DE RESPOSTA RÁPIDA
document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const modalCaption = document.getElementById('modalCaption');
    const closeModalButton = document.getElementById('closeModalButton');

    // --- Lógica de Token (sem alterações) ---
    let clientToken = null;
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');

    if (tokenFromUrl && tokenFromUrl.trim() !== '') {
        clientToken = tokenFromUrl.trim();
        console.log(`Token de cliente encontrado na URL: ${clientToken}`);
    } else {
        console.error("Token de cliente não encontrado na URL. O chat não funcionará.");
        addMessage('bot', 'ERRO: Token de acesso não fornecido na URL. Não é possível iniciar o chat.');
        userInput.disabled = true;
        sendButton.disabled = true;
        userInput.placeholder = "Acesso negado. Forneça um token na URL.";
    }

    // --- Funções de UI (sem alterações) ---
    function addMessage(sender, text, imageUrls = []) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        
        // Adiciona o texto se ele existir
        if (text) {
            const textElement = document.createElement('p');
            // Converte quebras de linha \n em tags <br> para exibição correta
            textElement.innerHTML = text.replace(/\n/g, '<br>');
            messageElement.appendChild(textElement);
        }

        // Adiciona as imagens se existirem
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
    
    // --- [INÍCIO DAS NOVAS MODIFICAÇÕES] ---

    /**
     * Remove qualquer container de botões de resposta rápida da tela.
     */
    function removeQuickReplies() {
        const existingContainer = document.querySelector('.quick-replies-container');
        if (existingContainer) {
            existingContainer.remove();
        }
    }

    /**
     * Renderiza os botões de resposta rápida na tela.
     * @param {Array<Object>} replies - Uma lista de objetos, cada um com 'title' e 'payload'.
     */
    function renderQuickReplies(replies) {
        removeQuickReplies(); // Garante que não haja botões duplicados

        if (!replies || replies.length === 0) {
            return; // Não faz nada se não houver botões
        }

        const container = document.createElement('div');
        container.className = 'quick-replies-container';

        replies.forEach(reply => {
            const button = document.createElement('button');
            button.className = 'quick-reply-button';
            button.textContent = reply.title;
            
            button.addEventListener('click', () => {
                // Ao clicar:
                // 1. Adiciona a mensagem do usuário (o texto do botão) à tela
                addMessage('user', reply.title);
                // 2. Envia o payload do botão para o servidor
                sendMessageToServer(reply.payload);
                // 3. Remove os botões da tela
                removeQuickReplies();
            });
            container.appendChild(button);
        });

        chatBox.appendChild(container);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    /**
     * Função principal para enviar uma mensagem.
     * Pega o texto do input, se houver, e chama a função que envia para o servidor.
     */
    function handleSendButtonClick() {
        const question = userInput.value.trim();
        if (question === '' || !clientToken) return;

        addMessage('user', question);
        userInput.value = '';
        sendMessageToServer(question);
    }

    /**
     * Função centralizada que envia a requisição para o backend.
     * @param {string} payload - O texto a ser enviado como a pergunta.
     */
    async function sendMessageToServer(payload) {
        if (!payload || !clientToken) {
            console.error("Tentativa de enviar mensagem sem um payload ou token válido.");
            return;
        }

        // Desabilita input enquanto espera a resposta
        userInput.disabled = true;
        sendButton.disabled = true;
        removeQuickReplies(); // Remove botões antigos antes de enviar nova mensagem

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    token: clientToken, 
                    question: payload 
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                addMessage('bot', `Erro do servidor: ${errorData.detail || 'Erro desconhecido'}`);
                throw new Error(`Erro na API: ${response.status}`);
            }

            const data = await response.json();
            // Adiciona a resposta do bot e em seguida renderiza os novos botões, se houver
            addMessage('bot', data.response, data.images);
            renderQuickReplies(data.quick_replies);

        } catch (error) {
            console.error('Erro de comunicação:', error);
            addMessage('bot', 'Falha na comunicação com o servidor.');
        } finally {
            // Reabilita o input
            userInput.disabled = false;
            sendButton.disabled = false;
            userInput.focus();
        }
    }

    // --- Event Listeners (Modificados) ---
    sendButton.addEventListener('click', handleSendButtonClick);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            handleSendButtonClick();
        }
    });

    if (clientToken) {
        userInput.focus();
    }
    // --- [FIM DAS MODIFICAÇÕES] ---
});