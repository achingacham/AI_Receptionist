const API_URL = "/api/chat";
const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

let conversationHistory = [];
let sessionId = null;

// ── Voice call ──────────────────────────────────────────────────────────────
let callFrame = null;
let inCall = false;

async function toggleCall() {
  if (inCall || callFrame) {
    endCall();
  } else {
    startCall();
  }
}

async function startCall() {
  const callBtn = document.getElementById("call-btn");
  const overlay = document.getElementById("call-overlay");
  const statusText = document.getElementById("call-status-text");

  if (!window.isSecureContext && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
    callBtn.disabled = true;
    overlay.style.display = "flex";
    statusText.textContent = "Voice calls require HTTPS or localhost. Please access this app over HTTPS.";
    return;
  }

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

    // ensure a user-gesture-created audio element for autoplay policies
    if (!window._remoteAudio) {
      window._remoteAudio = document.createElement('audio');
      window._remoteAudio.autoplay = true;
      window._remoteAudio.controls = true;
      window._remoteAudio.style.position = 'fixed';
      window._remoteAudio.style.right = '8px';
      window._remoteAudio.style.bottom = '8px';
      window._remoteAudio.style.zIndex = 9999;
      document.body.appendChild(window._remoteAudio);
      // create an enable-audio button and overlay the user can click if autoplay is blocked
      const audioEnabled = sessionStorage.getItem('audioEnabled') === '1';
      if (!audioEnabled) {
        if (!document.getElementById('enable-audio-btn')) {
          const btn = document.createElement('button');
          btn.id = 'enable-audio-btn';
          btn.textContent = 'Enable Audio';
          btn.style.position = 'fixed';
          btn.style.right = '8px';
          btn.style.bottom = '56px';
          btn.style.zIndex = 9999;
          btn.style.padding = '8px 12px';
          btn.style.background = '#0b5cff';
          btn.style.color = '#fff';
          btn.style.border = 'none';
          btn.style.borderRadius = '6px';
          btn.style.cursor = 'pointer';
          btn.onclick = async () => {
            try {
              await window._remoteAudio.play();
              sessionStorage.setItem('audioEnabled', '1');
              btn.style.display = 'none';
              const ov = document.getElementById('enable-audio-overlay'); if (ov) ov.style.display = 'none';
            } catch (e) {
              console.warn('Enable audio play failed', e);
            }
          };
          document.body.appendChild(btn);
        }

        if (!document.getElementById('enable-audio-overlay')) {
          const ov = document.createElement('div');
          ov.id = 'enable-audio-overlay';
          Object.assign(ov.style, {position:'fixed',left:0,top:0,right:0,bottom:0,background:'rgba(0,0,0,0.5)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:9998});
          ov.innerHTML = `<div style="background:#fff;padding:20px;border-radius:8px;text-align:center;max-width:90%;">Audio is disabled by your browser. <br/><br/><button id=\"enable-audio-overlay-btn\" style=\"padding:8px 12px;background:#0b5cff;color:#fff;border:none;border-radius:6px;cursor:pointer;\">Enable Audio</button></div>`;
          document.body.appendChild(ov);
          document.getElementById('enable-audio-overlay-btn').onclick = async () => {
            try {
              await window._remoteAudio.play();
              sessionStorage.setItem('audioEnabled', '1');
              const b = document.getElementById('enable-audio-btn'); if (b) b.style.display='none';
              ov.style.display = 'none';
            } catch (e) {
              console.warn('Overlay enable play failed', e);
            }
          };
        }
      }
    }

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

    // Attach remote audio to the user-gesture audio element when participants update
    callFrame.on('participant-updated', () => {
      try {
        const parts = Object.values(callFrame.participants());
        const remote = parts.find(p => !p.local && (p?.audioTrack || p?.tracks?.audio?.stream));
        if (remote) {
          const track = remote.audioTrack || (remote.tracks && remote.tracks.audio && remote.tracks.audio.stream && remote.tracks.audio.stream.getAudioTracks()[0]);
          if (track) {
            window._remoteAudio.srcObject = new MediaStream([track]);
            // try to play automatically; if blocked, show overlay/button unless user previously enabled
            const audioEnabled = sessionStorage.getItem('audioEnabled') === '1';
            window._remoteAudio.play().then(()=>{
              if (!audioEnabled) {
                sessionStorage.setItem('audioEnabled','1');
              }
              const b=document.getElementById('enable-audio-btn'); if(b) b.style.display='none';
              const ov=document.getElementById('enable-audio-overlay'); if(ov) ov.style.display='none';
            }).catch(()=>{
              if (!audioEnabled) {
                const b=document.getElementById('enable-audio-btn'); if(b) b.style.display='inline-block';
                const ov=document.getElementById('enable-audio-overlay'); if(ov) ov.style.display='flex';
              }
            });
          }
        }
      } catch (e) {
        console.warn('Failed to attach remote audio track', e);
      }
    });

    callFrame.on("left-meeting", () => {
      endCall();
    });

    callFrame.on("error", (e) => {
      console.error("Daily error:", e);
      statusText.textContent = `Call error: ${e?.message || e}`;
      callBtn.disabled = false;
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
      body: JSON.stringify({ messages: conversationHistory, session_id: sessionId }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Request failed");
    }

    const data = await res.json();
    removeTyping();

    sessionId = data.session_id;
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
