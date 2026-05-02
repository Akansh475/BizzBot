# 🤖 BizBot — AI-Powered FAQ Chatbot for Small Businesses

BizBot is a plug-and-play AI chatbot that any small business can add to their website in minutes. It answers customer questions automatically, captures leads, and emails the business owner instantly — all powered by a free AI model.

---

## ✨ Features

- 💬 **AI-powered chat** — answers customer FAQs using a plain text knowledge base
- 🏢 **Multi-business support** — one server handles unlimited businesses
- 📋 **Lead capture** — collects name & phone when the bot can't answer
- 📧 **Instant email alerts** — notifies the business owner the moment a lead comes in
- 🧠 **Conversation memory** — remembers context within a session
- 🛡️ **Rate limiting** — prevents abuse (20 messages per session per hour)
- 📱 **Mobile responsive** — full-screen chat on phones
- 🔌 **Easy embed** — any website adds it with just 2 lines of code

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, flask-cors |
| AI | Groq API — `llama-3.1-8b-instant` (free tier) |
| Email | Python smtplib + Gmail SMTP |
| Frontend | Vanilla HTML / CSS / JS (no frameworks) |
| Deploy | Render.com + Gunicorn |

---

## 📁 Folder Structure

```
Bizz/
├── app.py                  # Flask server — all API routes
├── bot.py                  # AI logic — Groq API calls
├── config.py               # Central settings
├── requirements.txt        # Python dependencies
├── render.yaml             # Render.com deployment config
├── demo.html               # Demo restaurant website
├── .env                    # Secret keys (never commit this)
├── .env.example            # Template for .env
├── businesses/
│   ├── himalayan_kitchen.txt   # Sample: restaurant
│   └── sparkle_salon.txt       # Sample: salon
├── static/
│   └── embed.js            # Embeddable chat widget
└── leads/                  # Auto-created, stores lead JSON files
```

---

## ⚡ Quick Start (Local)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/BizBot.git
cd BizBot/Bizz
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in:
```
GROQ_API_KEY=your_groq_api_key
EMAIL_SENDER=yourgmail@gmail.com
EMAIL_APP_PASSWORD=your_16_char_app_password
```

> **Getting a Groq API key:** Sign up free at [console.groq.com](https://console.groq.com)
> **Getting a Gmail App Password:** myaccount.google.com → Security → 2-Step Verification → App Passwords

### 5. Run the server
```bash
python3 app.py
```

### 6. Open the demo
Open `demo.html` in your browser — you'll see a live chatbot on a fake restaurant website.

---

## 🔌 Embedding on a Client's Website

Add these 2 lines before the closing `</body>` tag of any website:

```html
<script>
  window.ChatbotConfig = {
    business_id: "himalayan_kitchen",
    botName:     "Kitchen Assistant",
    themeColor:  "#e65c00",
    serverUrl:   "https://your-render-url.onrender.com"
  };
</script>
<script src="https://your-render-url.onrender.com/static/embed.js"></script>
```

**On WordPress:** Appearance → Theme Editor → footer.php → paste before `</body>`

---

## ➕ Adding a New Business

1. Create `businesses/your_business_name.txt`
2. Add `OWNER_EMAIL: owner@email.com` as the first line
3. Fill in business info (name, hours, services, FAQs, etc.)
4. Restart the server

That's it. No code changes needed.

---

## 🚀 Deploy to Render (Free)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml`
5. Add environment variables in the Render dashboard:
   - `GROQ_API_KEY`
   - `EMAIL_SENDER`
   - `EMAIL_APP_PASSWORD`
6. Click **Deploy** — your bot is live!

---

## 📡 API Routes

| Method | Route | Description |
|---|---|---|
| GET | `/health` | Server health check |
| GET | `/businesses` | List all business IDs |
| POST | `/chat` | Send a message, get AI reply |
| POST | `/capture-lead` | Save lead + email owner |
| DELETE | `/clear/<session_id>` | Clear conversation history |

---

## 👨‍💻 Built By

**Akansh Mehra** — [github.com/YOUR_USERNAME](https://github.com/YOUR_USERNAME)

---

## 📄 License

MIT — free to use, modify, and sell.