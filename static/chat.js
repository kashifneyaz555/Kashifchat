const socket = io();
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const usernameModal = new bootstrap.Modal(document.getElementById("usernameModal"));
const usernameInput = document.getElementById("usernameInput");
const typingIndicator = document.getElementById("typingIndicator");
const typingText = document.querySelector(".typing-text");
const notificationSound = document.getElementById("notificationSound");

let username = "";
let typingTimer;
let isTyping = false;

window.onload = () => {
    usernameModal.show();
};

function joinChat() {
    username = usernameInput.value.trim();
    if (!username) return;
    socket.emit("join_chat", { username });
    messageInput.disabled = false;
    sendButton.disabled = false;
    usernameModal.hide();
}

function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    socket.emit("send_message", { username, message });
    messageInput.value = "";
    stopTyping();
}

function deleteMessage(id) {
    fetch("/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id })
    });
}

messageInput.addEventListener("input", () => {
    if (!isTyping) {
        isTyping = true;
        socket.emit("typing", { username });
    }
    clearTimeout(typingTimer);
    typingTimer = setTimeout(stopTyping, 1000);
});

function stopTyping() {
    if (isTyping) {
        isTyping = false;
        socket.emit("stop_typing", { username });
    }
}

socket.on("receive_message", data => {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message " + (data.type === "system" ? "system" : data.username === username ? "sent" : "received");
    msgDiv.dataset.id = data.id;

    let html = `<div class="message-bubble">`;
    if (data.type !== "system" && data.username !== username) {
        html += `<div class="message-header">${data.username}</div>`;
    }
    html += `<div class="message-text">${data.message}</div><div class="message-time">${data.timestamp}</div>`;
    if (data.username === username && data.type === "user") {
        html += `<button class="btn btn-sm btn-outline-danger ms-2" onclick="deleteMessage(${data.id})">🗑️</button>`;
    }
    html += `</div>`;
    msgDiv.innerHTML = html;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    if (data.username !== username && data.type === "user") {
        notificationSound.play();
    }
});

socket.on("message_deleted", data => {
    const messages = chatMessages.querySelectorAll(".message");
    messages.forEach(msg => {
        if (msg.dataset.id == data.id) {
            msg.remove();
        }
    });
});

socket.on("user_typing", data => {
    typingText.textContent = `${data.username} is typing...`;
    typingIndicator.style.display = "block";
});

socket.on("user_stop_typing", () => {
    typingIndicator.style.display = "none";
});