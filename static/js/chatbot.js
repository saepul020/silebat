/* ========================================
   CHATBOT PUBLIC JS
   Chatbot ringan untuk landing page SILEBAT.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initPublicChatbot();
});

function initPublicChatbot() {
    const chatToggle = document.getElementById('chatToggle');
    const chatWindow = document.getElementById('chatWindow');
    const chatBody = document.getElementById('chatBody');
    const chatInput = document.getElementById('chatInput');
    const chatSend = document.getElementById('chatSend');
    let chatOpened = false;

    if (!chatToggle || !chatWindow || !chatBody || !chatInput || !chatSend) {
        return;
    }

    chatToggle.addEventListener('click', function () {
        chatToggle.classList.toggle('open');
        chatWindow.classList.toggle('open');
        if (!chatOpened) {
            chatOpened = true;
            window.setTimeout(function () {
                addBotMsg('Halo! 👋 Saya asisten virtual Laboratorium Balai Air Tanah. Ada yang bisa saya bantu?');
            }, 350);
        }
    });

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    function addBotMsg(text) {
        addMessage(text, 'bot');
    }

    function addUserMsg(text) {
        addMessage(text, 'user');
    }

    function addMessage(text, type) {
        const msg = document.createElement('div');
        msg.className = 'msg ' + type;
        msg.textContent = text;
        chatBody.appendChild(msg);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function showTyping() {
        const typing = document.createElement('div');
        typing.className = 'msg bot typing-indicator';
        typing.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
        chatBody.appendChild(typing);
        chatBody.scrollTop = chatBody.scrollHeight;
        return typing;
    }

    function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) {
            return;
        }

        addUserMsg(text);
        chatInput.value = '';
        const typing = showTyping();

        fetch('/chatbot/reply/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                typing.remove();
                addBotMsg(data.reply || 'Terima kasih, pesan Anda sudah diterima.');
            })
            .catch(function () {
                typing.remove();
                addBotMsg('Maaf, asisten virtual belum dapat memproses pesan saat ini. Silakan hubungi kontak resmi laboratorium.');
            });
    }
}
