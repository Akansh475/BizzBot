/*
  embed.js — BizBot Embeddable Chat Widget
  =========================================
  Any website can load this chatbot by adding two lines to their HTML:

    <script>
      window.ChatbotConfig = {
        business_id: "himalayan_kitchen",   // must match your .txt filename
        botName:     "Kitchen Assistant",   // name shown in chat header
        themeColor:  "#e65c00",             // any hex color
        serverUrl:   "http://localhost:5000" // your Flask server URL
      }
    </script>
    <script src="http://localhost:5000/static/embed.js"></script>

  All CSS classes use "cb-" prefix to avoid clashing with the host website's styles.
  All HTML is injected dynamically — nothing is hardcoded in the host page.
*/

(function () {
  // ── 1. Read Config ───────────────────────────────────────────────────────────
  // Read settings from window.ChatbotConfig, with sensible defaults
  var config = window.ChatbotConfig || {};
  var BUSINESS_ID  = config.business_id || "himalayan_kitchen";
  var BOT_NAME     = config.botName     || "BizBot Assistant";
  var THEME_COLOR  = config.themeColor  || "#4f46e5";
  var SERVER_URL   = config.serverUrl   || "http://localhost:5000";

  // Generate a unique session ID for this visitor
  // Math.random().toString(36) gives something like "0.abc123xyz"
  // .substr(2, 9) strips the "0." to give "abc123xyz"
  var SESSION_ID = "sess_" + Math.random().toString(36).substr(2, 9);

  // Track whether the lead form has been shown yet
  var leadCaptured = false;

  // ── 2. Inject CSS ────────────────────────────────────────────────────────────
  // We create a <style> tag and inject all our CSS into the page
  // Every class starts with "cb-" so it never conflicts with the site's CSS
  var style = document.createElement("style");
  style.innerHTML = `
    /* ── Reset & Font ── */
    .cb-widget * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    /* ── Floating Button ── */
    #cb-toggle-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: ${THEME_COLOR};
      color: white;
      border: none;
      cursor: pointer;
      font-size: 26px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s ease;
    }
    #cb-toggle-btn:hover { transform: scale(1.1); }

    /* ── Chat Panel ── */
    #cb-panel {
      position: fixed;
      bottom: 92px;
      right: 24px;
      width: 360px;
      height: 500px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.18);
      display: flex;
      flex-direction: column;
      z-index: 99998;
      overflow: hidden;
      opacity: 0;
      transform: translateY(16px);
      pointer-events: none;
      transition: opacity 0.25s ease, transform 0.25s ease;
    }
    #cb-panel.cb-open {
      opacity: 1;
      transform: translateY(0);
      pointer-events: all;
    }

    /* ── Header ── */
    .cb-header {
      background: ${THEME_COLOR};
      color: white;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .cb-avatar {
      width: 36px;
      height: 36px;
      background: rgba(255,255,255,0.25);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }
    .cb-header-info { flex: 1; }
    .cb-header-name { font-weight: 700; font-size: 15px; }
    .cb-header-status { font-size: 11px; opacity: 0.85; }
    .cb-close-btn {
      background: none;
      border: none;
      color: white;
      font-size: 20px;
      cursor: pointer;
      opacity: 0.8;
      line-height: 1;
    }
    .cb-close-btn:hover { opacity: 1; }

    /* ── Messages Area ── */
    .cb-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #f8f9fa;
    }

    /* ── Individual Message Bubbles ── */
    .cb-msg {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 14px;
      font-size: 13.5px;
      line-height: 1.5;
      word-wrap: break-word;
    }
    .cb-msg.cb-bot {
      background: white;
      color: #1a1a1a;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .cb-msg.cb-user {
      background: ${THEME_COLOR};
      color: white;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }

    /* ── Typing Indicator ── */
    .cb-typing {
      display: flex;
      gap: 4px;
      padding: 10px 14px;
      background: white;
      border-radius: 14px;
      border-bottom-left-radius: 4px;
      align-self: flex-start;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .cb-typing span {
      width: 7px;
      height: 7px;
      background: #adb5bd;
      border-radius: 50%;
      animation: cb-bounce 1.2s infinite;
    }
    .cb-typing span:nth-child(2) { animation-delay: 0.2s; }
    .cb-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes cb-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30%            { transform: translateY(-6px); }
    }

    /* ── Lead Capture Form ── */
    .cb-lead-form {
      background: white;
      border: 1.5px solid ${THEME_COLOR};
      border-radius: 14px;
      padding: 14px;
      align-self: stretch;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .cb-lead-form p {
      font-size: 13px;
      color: #444;
      font-weight: 600;
    }
    .cb-lead-form input {
      padding: 8px 10px;
      border: 1px solid #dee2e6;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      width: 100%;
    }
    .cb-lead-form input:focus { border-color: ${THEME_COLOR}; }
    .cb-lead-form button {
      background: ${THEME_COLOR};
      color: white;
      border: none;
      border-radius: 8px;
      padding: 9px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .cb-lead-form button:hover { opacity: 0.9; }

    /* ── Input Bar ── */
    .cb-input-bar {
      display: flex;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid #e9ecef;
      background: white;
    }
    .cb-input-bar input {
      flex: 1;
      padding: 9px 12px;
      border: 1px solid #dee2e6;
      border-radius: 20px;
      font-size: 13.5px;
      outline: none;
    }
    .cb-input-bar input:focus { border-color: ${THEME_COLOR}; }
    .cb-send-btn {
      background: ${THEME_COLOR};
      color: white;
      border: none;
      border-radius: 50%;
      width: 36px;
      height: 36px;
      cursor: pointer;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .cb-send-btn:hover { opacity: 0.9; }

    /* ── Mobile: full screen under 480px ── */
    @media (max-width: 480px) {
      #cb-panel {
        width: 100%;
        height: 100%;
        bottom: 0;
        right: 0;
        border-radius: 0;
      }
      #cb-toggle-btn {
        bottom: 16px;
        right: 16px;
      }
    }
  `;
  document.head.appendChild(style);

  // ── 3. Inject HTML ───────────────────────────────────────────────────────────
  // Build the chat widget HTML as a string and inject it into <body>
  var container = document.createElement("div");
  container.className = "cb-widget";
  container.innerHTML = `
    <!-- Floating toggle button -->
    <button id="cb-toggle-btn" title="Chat with us">💬</button>

    <!-- Chat panel -->
    <div id="cb-panel">

      <!-- Header -->
      <div class="cb-header">
        <div class="cb-avatar">🤖</div>
        <div class="cb-header-info">
          <div class="cb-header-name">${BOT_NAME}</div>
          <div class="cb-header-status">● Online — here to help</div>
        </div>
        <button class="cb-close-btn" id="cb-close-btn">✕</button>
      </div>

      <!-- Messages -->
      <div class="cb-messages" id="cb-messages"></div>

      <!-- Input bar -->
      <div class="cb-input-bar">
        <input type="text" id="cb-input" placeholder="Type your message..." />
        <button class="cb-send-btn" id="cb-send-btn">➤</button>
      </div>

    </div>
  `;
  document.body.appendChild(container);

  // ── 4. Get References to DOM Elements ───────────────────────────────────────
  var panel      = document.getElementById("cb-panel");
  var toggleBtn  = document.getElementById("cb-toggle-btn");
  var closeBtn   = document.getElementById("cb-close-btn");
  var messagesEl = document.getElementById("cb-messages");
  var inputEl    = document.getElementById("cb-input");
  var sendBtn    = document.getElementById("cb-send-btn");

  // ── 5. Open / Close Panel ───────────────────────────────────────────────────
  var isOpen = false;

  function openPanel() {
    isOpen = true;
    panel.classList.add("cb-open");
    toggleBtn.innerHTML = "✕";
    inputEl.focus();

    // Show welcome message only on first open
    if (messagesEl.children.length === 0) {
      addBotMessage("👋 Hi! I'm " + BOT_NAME + ". How can I help you today?");
    }
  }

  function closePanel() {
    isOpen = false;
    panel.classList.remove("cb-open");
    toggleBtn.innerHTML = "💬";
  }

  toggleBtn.addEventListener("click", function () {
    isOpen ? closePanel() : openPanel();
  });

  closeBtn.addEventListener("click", closePanel);

  // ── 6. Add Messages to Chat ─────────────────────────────────────────────────

  function addBotMessage(text) {
    var div = document.createElement("div");
    div.className = "cb-msg cb-bot";
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
  }

  function addUserMessage(text) {
    var div = document.createElement("div");
    div.className = "cb-msg cb-user";
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ── 7. Typing Indicator ──────────────────────────────────────────────────────

  function showTyping() {
    var div = document.createElement("div");
    div.className = "cb-typing";
    div.id = "cb-typing";
    div.innerHTML = "<span></span><span></span><span></span>";
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function hideTyping() {
    var el = document.getElementById("cb-typing");
    if (el) el.remove();
  }

  // ── 8. Lead Capture Form ─────────────────────────────────────────────────────

  function showLeadForm() {
    // Don't show it twice
    if (leadCaptured) return;

    var form = document.createElement("div");
    form.className = "cb-lead-form";
    form.id = "cb-lead-form";
    form.innerHTML = `
      <p>📋 Leave your details and we'll call you back!</p>
      <input type="text"  id="cb-lead-name"  placeholder="Your name" />
      <input type="tel"   id="cb-lead-phone" placeholder="Your phone number" />
      <button id="cb-lead-submit">Send my details →</button>
    `;
    messagesEl.appendChild(form);
    scrollToBottom();

    // Handle form submission
    document.getElementById("cb-lead-submit").addEventListener("click", function () {
      var name  = document.getElementById("cb-lead-name").value.trim();
      var phone = document.getElementById("cb-lead-phone").value.trim();

      if (!name || !phone) {
        alert("Please enter both your name and phone number.");
        return;
      }

      submitLead(name, phone, form);
    });
  }

  function submitLead(name, phone, formEl) {
    // Disable the button to prevent double submission
    document.getElementById("cb-lead-submit").disabled = true;
    document.getElementById("cb-lead-submit").textContent = "Sending...";

    fetch(SERVER_URL + "/capture-lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name:        name,
        phone:       phone,
        session_id:  SESSION_ID,
        business_id: BUSINESS_ID,
      }),
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      // Remove the form and show a thank-you message
      formEl.remove();
      leadCaptured = true;
      addBotMessage("✅ Thanks, " + name + "! Our team will contact you on " + phone + " shortly.");
    })
    .catch(function () {
      addBotMessage("Sorry, something went wrong. Please call us directly.");
    });
  }

  // ── 9. Send Message ──────────────────────────────────────────────────────────

  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text) return;

    // Show user message and clear input
    addUserMessage(text);
    inputEl.value = "";

    // Show typing dots while waiting for response
    showTyping();

    // Call the Flask /chat route
    fetch(SERVER_URL + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message:     text,
        session_id:  SESSION_ID,
        business_id: BUSINESS_ID,
      }),
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      hideTyping();
      addBotMessage(data.response);

      // If AI triggered handoff, show the lead capture form
      if (data.needs_handoff && !leadCaptured) {
        showLeadForm();
      }
    })
    .catch(function () {
      hideTyping();
      addBotMessage("I'm having trouble connecting. Please try again.");
    });
  }

  // Send on button click
  sendBtn.addEventListener("click", sendMessage);

  // Send on Enter key
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendMessage();
  });

  // ── 10. Auto-open after 3 seconds (optional, comment out if unwanted) ────────
  // setTimeout(openPanel, 3000);

})();
// The entire widget is wrapped in (function(){ ... })() 
// This is called an IIFE (Immediately Invoked Function Expression)
// It means all our variables stay private and never clash with the host website