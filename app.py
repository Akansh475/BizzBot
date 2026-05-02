"""
app.py — BizBot Flask Backend
=============================================================
PRE-CLIENT CHECKLIST (verify all 8 before showing a client):
  [ ] 1. GROQ_API_KEY is set in .env and is valid
  [ ] 2. EMAIL_SENDER is set in .env (Gmail address)
  [ ] 3. EMAIL_APP_PASSWORD is set in .env (Gmail App Password, not normal password)
  [ ] 4. Each business .txt file has OWNER_EMAIL on the first line
  [ ] 5. leads/ folder exists (or will be auto-created on first lead)
  [ ] 6. flask-cors is installed (pip install flask-cors)
  [ ] 7. All packages in requirements.txt are installed in venv
  [ ] 8. Tested /health, /chat, and /capture-lead with a real form submission
=============================================================
"""

import os
import json
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify
from flask_cors import CORS

from bot import get_reply, clear_history
from config import (
    BUSINESSES_FOLDER,
    LEADS_FOLDER,
    EMAIL_SENDER,
    EMAIL_APP_PASSWORD,
    SMTP_HOST,
    SMTP_PORT,
)

# ── App Setup ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Rate Limiting ──────────────────────────────────────────────────────────────
# Tracks message count per session in memory
# Structure: { session_id: { "count": 5, "window_start": datetime } }
rate_limit_store = {}
RATE_LIMIT_MAX    = 20
RATE_LIMIT_WINDOW = timedelta(hours=1)

def is_rate_limited(session_id):
    """
    Returns True if this session sent 20+ messages in the last hour.
    Resets automatically after 1 hour. No Redis needed.
    """
    now = datetime.now()

    if session_id not in rate_limit_store:
        rate_limit_store[session_id] = {"count": 1, "window_start": now}
        return False

    entry = rate_limit_store[session_id]

    if now - entry["window_start"] > RATE_LIMIT_WINDOW:
        rate_limit_store[session_id] = {"count": 1, "window_start": now}
        return False

    if entry["count"] >= RATE_LIMIT_MAX:
        return True

    entry["count"] += 1
    return False

# ── Helper: Read Owner Email ───────────────────────────────────────────────────

def get_owner_email(business_id):
    """
    Reads OWNER_EMAIL from the first line of the business .txt file.
    Expected format:  OWNER_EMAIL: owner@example.com
    Returns the email string, or None if not found.
    """
    file_path = os.path.join(BUSINESSES_FOLDER, f"{business_id}.txt")

    if not os.path.exists(file_path):
        logger.warning(f"Business file not found: {file_path}")
        return None

    try:
        with open(file_path, "r") as f:
            first_line = f.readline().strip()

        if first_line.lower().startswith("owner_email:"):
            return first_line.split(":", 1)[1].strip()
        else:
            logger.warning(f"No OWNER_EMAIL in first line of {file_path}")
            return None

    except Exception as e:
        logger.error(f"Error reading owner email: {e}")
        return None

# ── Helper: Save Lead ──────────────────────────────────────────────────────────

def save_lead(business_id, name, phone, session_id, last_question):
    """
    Saves lead to leads/{business_id}_leads.json
    Auto-creates leads/ folder if missing.
    Returns True on success, False on failure.
    """
    os.makedirs(LEADS_FOLDER, exist_ok=True)
    file_path = os.path.join(LEADS_FOLDER, f"{business_id}_leads.json")

    lead = {
        "name": name,
        "phone": phone,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "last_question": last_question,
    }

    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                leads = json.load(f)
        else:
            leads = []

        leads.append(lead)

        with open(file_path, "w") as f:
            json.dump(leads, f, indent=2)

        logger.info(f"Lead saved: {name} | {phone} | {business_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to save lead: {e}")
        return False

# ── Helper: Send Email ─────────────────────────────────────────────────────────

def send_email_notification(business_id, owner_email, name, phone, last_question):
    """
    Sends lead notification email via Gmail SMTP.
    Always returns True/False — never raises an exception.
    Email failure never breaks the user-facing flow.
    """
    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD:
        logger.warning("Email credentials missing in .env — skipping email")
        return False

    if not owner_email:
        logger.warning(f"No owner email for '{business_id}' — skipping email")
        return False

    subject = f"New Lead from your chatbot — {business_id}"
    body = f"""Hello,

You have a new lead from your BizBot chatbot!

Name:           {name}
Phone:          {phone}
Last Question:  {last_question}
Business:       {business_id}
Time:           {datetime.now().strftime("%d %b %Y, %I:%M %p")}

Please follow up with them soon.

— BizBot Notification System
"""

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = owner_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_SENDER, owner_email, msg.as_string())
        server.quit()
        logger.info(f"Email sent to {owner_email} for {business_id}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail auth failed — use an App Password, not your normal password. "
            "Enable 2-Step Verification at myaccount.google.com first."
        )
        return False

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected email error: {e}")
        return False

# ── Route: Health Check ────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Confirms the server is running. Used by Render for health checks."""
    return jsonify({"status": "ok", "message": "BizBot is running!"})

# ── Route: List Businesses ─────────────────────────────────────────────────────

@app.route("/businesses", methods=["GET"])
def list_businesses():
    """
    Scans the businesses/ folder and returns all available business IDs.
    Example response: { "businesses": ["himalayan_kitchen", "sparkle_salon"] }
    """
    try:
        if not os.path.exists(BUSINESSES_FOLDER):
            return jsonify({"businesses": []})

        files = os.listdir(BUSINESSES_FOLDER)
        business_ids = [
            f.replace(".txt", "")
            for f in files
            if f.endswith(".txt")
        ]
        return jsonify({"businesses": sorted(business_ids)})

    except Exception as e:
        logger.error(f"Error listing businesses: {e}")
        return jsonify({"businesses": [], "error": "Could not read businesses folder"}), 500

# ── Route: Chat ────────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    """
    Main chat route. Accepts a message and returns AI response.
    Includes rate limiting — max 20 messages per session per hour.
    Expected JSON: { message, session_id, business_id }
    """
    try:
        data = request.get_json()

        if not data or not data.get("message"):
            return jsonify({"error": "No message provided"}), 400

        message     = data.get("message", "").strip()
        session_id  = data.get("session_id", "default")
        business_id = data.get("business_id", "himalayan_kitchen")

        # Rate limit check
        if is_rate_limited(session_id):
            logger.warning(f"Rate limit hit for session: {session_id}")
            return jsonify({
                "response": "You've sent a lot of messages! Please wait a while before trying again.",
                "needs_handoff": False,
                "rate_limited": True,
            }), 429

        # Validate business exists
        business_file = os.path.join(BUSINESSES_FOLDER, f"{business_id}.txt")
        if not os.path.exists(business_file):
            logger.warning(f"Unknown business_id: {business_id}")
            return jsonify({
                "response": "Sorry, I couldn't find information for this business.",
                "needs_handoff": False,
            }), 404

        # Get AI response
        result = get_reply(message, session_id, business_id)

        return jsonify({
            "response": result["reply"],
            "needs_handoff": result["needs_handoff"],
        })

    except FileNotFoundError as e:
        logger.error(f"Business file not found: {e}")
        return jsonify({
            "response": "Sorry, I can't find information for this business right now.",
            "needs_handoff": False,
        }), 404

    except Exception as e:
        logger.error(f"Unexpected error in /chat: {e}")
        return jsonify({
            "response": "Sorry, something went wrong. Please try again in a moment.",
            "needs_handoff": False,
        }), 500

# ── Route: Capture Lead ────────────────────────────────────────────────────────

@app.route("/capture-lead", methods=["POST"])
def capture_lead():
    """
    Saves a lead and emails the business owner.
    Always returns success to frontend — email failure is silent.
    Expected JSON: { name, phone, session_id, business_id }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        name        = data.get("name", "").strip()
        phone       = data.get("phone", "").strip()
        session_id  = data.get("session_id", "unknown")
        business_id = data.get("business_id", "himalayan_kitchen")

        if not name or not phone:
            return jsonify({"error": "Name and phone are required"}), 400

        # Basic phone validation — must have at least 7 digits
        digits = [c for c in phone if c.isdigit()]
        if len(digits) < 7:
            return jsonify({"error": "Please enter a valid phone number"}), 400

        # Get last user question from bot history
        from bot import chat_histories
        history = chat_histories.get(session_id, [])
        last_question = "Not available"
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_question = msg.get("content", "Not available")
                break

        # Save lead to file
        saved = save_lead(business_id, name, phone, session_id, last_question)
        if not saved:
            return jsonify({
                "success": False,
                "message": "Something went wrong. Please try again.",
            }), 500

        # Send email notification (failure is OK — lead already saved)
        owner_email = get_owner_email(business_id)
        email_sent  = send_email_notification(
            business_id, owner_email, name, phone, last_question
        )

        if not email_sent:
            logger.warning(f"Lead saved for {name} but email failed (owner: {owner_email})")

        return jsonify({
            "success": True,
            "message": "Thanks! Our team will contact you soon.",
            "email_sent": email_sent,
        })

    except Exception as e:
        logger.error(f"Unexpected error in /capture-lead: {e}")
        return jsonify({
            "success": False,
            "message": "Something went wrong. Please try again.",
        }), 500

# ── Route: Clear Session ───────────────────────────────────────────────────────

@app.route("/clear/<session_id>", methods=["DELETE"])
def clear_session(session_id):
    """Clears conversation history and rate limit for a session."""
    try:
        clear_history(session_id)
        if session_id in rate_limit_store:
            del rate_limit_store[session_id]
        return jsonify({"message": f"Session {session_id} cleared."})
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        return jsonify({"error": "Could not clear session"}), 500

# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # debug=True for local development only
    # On Render, gunicorn runs the app — see render.yaml
    app.run(debug=True, port=5000)