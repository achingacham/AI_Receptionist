const API_URL = "/api/appointment";
const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

let conversationHistory = [];

// ── Voice call ──────────────────────────────────────────────────────────────
let callFrame = null;
let inCall = false;

async function toggleCall() {
  if (inCall) {
    endCall();
  } else {
    startCall();
  }
}

async function startCall() {
  const callBtn = document.getElementById("call-btn");
  const overlay = document.getElementById("call-overlay");
  const statusText = document.getElementById("call-status-text");

  callBtn.disabled = true;
  overlay.style.display = "flex";
  statusText.textContent = "Connecting...";

  try {
    const res = await fetch("/api/voice/start", { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to start call");
    }
    const { room_url, token } = await res.json();

    callFrame = window.DailyIframe.createCallObject({
      audioSource: true,
      videoSource: false,
    });

    callFrame.on("joined-meeting", () => {
      statusText.textContent = "On call with Kiran...";
      inCall = true;
      callBtn.disabled = false;
      callBtn.classList.add("active-call");
    });

    callFrame.on("left-meeting", () => {
      endCall();
    });

    callFrame.on("error", (e) => {
      console.error("Daily error:", e);
      endCall();
    });

    await callFrame.join({ url: room_url, token });
  } catch (err) {
    console.error(err);
    statusText.textContent = "Failed to connect. Try again.";
    callBtn.disabled = false;
    setTimeout(() => { overlay.style.display = "none"; }, 3000);
  }
}

function endCall() {
  if (callFrame) {
    callFrame.destroy();
    callFrame = null;
  }
  inCall = false;
  const callBtn = document.getElementById("call-btn");
  callBtn.disabled = false;
  callBtn.classList.remove("active-call");
  document.getElementById("call-overlay").style.display = "none";
}
// ────────────────────────────────────────────────────────────────────────────

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
