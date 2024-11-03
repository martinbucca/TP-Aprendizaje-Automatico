document.getElementById('send-btn').addEventListener('click', async () => {
    const queryInput = document.getElementById('query-input');
    const query = queryInput.value.trim();

    if (query === '') return;

    // Agrega el mensaje del usuario al chat
    addMessage(query, 'user-message');
    queryInput.value = '';

    // Muestra el spinner de carga
    document.getElementById('loading-spinner').style.display = 'block';

    try {
        const response = await fetch('http://127.0.0.1:5000/find_chunk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });

        const data = await response.json();
        addMessage(data.answer, 'bot-message');
    } catch (error) {
        addMessage("Error al obtener respuesta del servidor.", 'bot-message');
    } finally {
        // Oculta el spinner de carga cuando se recibe una respuesta
        document.getElementById('loading-spinner').style.display = 'none';
    }
});

// Función para agregar mensajes al chat
function addMessage(message, className) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${className}`;
    messageDiv.textContent = message;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight; // Desplaza hacia el último mensaje
}

// Envía el mensaje al presionar Enter
document.getElementById('query-input').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        document.getElementById('send-btn').click();
    }
});
