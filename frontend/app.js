const API_URL = "/api/chat";
const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

let conversationHistory = [];

// Auto-resize textarea
userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
});

// Send on Enter (Shift+Enter for newline)
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

function appendMessage(role, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  msgDiv.appendChild(bubble);
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
}

function showTyping() {
  const msgDiv = document.createElement("div");
  msgDiv.className = "message assistant typing";
  msgDiv.id = "typing-indicator";
  msgDiv.innerHTML = `<div class="bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>`;
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = "";
  userInput.style.height = "auto";
  sendBtn.disabled = true;

  appendMessage("user", text);
  conversationHistory.push({ role: "user", content: text });

  showTyping();

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: conversationHistory }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Request failed");
    }

    const data = await res.json();
    removeTyping();

    appendMessage("assistant", data.reply);
    conversationHistory.push({ role: "assistant", content: data.reply });
  } catch (err) {
    removeTyping();
    appendMessage("assistant", "Sorry, I'm having trouble connecting right now. Please try again shortly.");
    console.error(err);
    // Remove the failed user message from history
    conversationHistory.pop();
  } finally {
    sendBtn.disabled = false;
    userInput.focus();
  }
}
