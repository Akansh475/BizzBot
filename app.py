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
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify
from flask_cors import CORS

# bot.py uses get_reply() and clear_history() — matching exactly
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

# ── Helper: Read Owner Email from .txt file ────────────────────────────────────

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
            logger.warning(f"No OWNER_EMAIL found in first line of {file_path}")
            return None

    except Exception as e:
        logger.error(f"Error reading owner email: {e}")
        return None

# ── Helper: Save Lead to JSON File ────────────────────────────────────────────

def save_lead(business_id, name, phone, session_id, last_question):
    """
    Saves lead to leads/{business_id}_leads.json
    Creates the leads/ folder automatically if it doesn't exist.
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

# ── Helper: Send Email Notification ───────────────────────────────────────────

def send_email_notification(business_id, owner_email, name, phone, last_question):
    """
    Sends an email to the business owner via Gmail SMTP.
    If anything goes wrong, logs the error and returns False.
    Never crashes the app — email failure is always handled gracefully.
    """
    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD:
        logger.warning("Email credentials not set in .env — skipping email")
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
        logger.info(f"Email sent to {owner_email} for business {business_id}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. "
            "Use an App Password, not your normal Gmail password. "
            "Enable 2-Step Verification first at myaccount.google.com"
        )
        return False

    except Exception as e:
        logger.error(f"Email error: {e}")
        return False

# ── Route: Health Check ────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "BizBot is running!"})

# ── Route: Chat ────────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    """
    Receives a user message, passes it to bot.py, returns AI response.
    bot.py handles history internally — we just pass session_id and business_id.
    """
    data = request.get_json()

    if not data or not data.get("message"):
        return jsonify({"error": "No message provided"}), 400

    message     = data.get("message", "").strip()
    session_id  = data.get("session_id", "default")
    business_id = data.get("business_id", "himalayan_kitchen")

    try:
        # get_reply() returns {"reply": "...", "needs_handoff": True/False}
        result = get_reply(message, session_id, business_id)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        return jsonify({
            "response": "Sorry, I'm having trouble right now. Please try again.",
            "needs_handoff": False,
        })

    return jsonify({
        "response": result["reply"],
        "needs_handoff": result["needs_handoff"],
    })

# ── Route: Capture Lead ────────────────────────────────────────────────────────

@app.route("/capture-lead", methods=["POST"])
def capture_lead():
    """
    Saves a lead and emails the business owner.
    Always returns success to the frontend — email failure is handled silently.

    Expected JSON: { name, phone, session_id, business_id }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400

    name        = data.get("name", "").strip()
    phone       = data.get("phone", "").strip()
    session_id  = data.get("session_id", "unknown")
    business_id = data.get("business_id", "himalayan_kitchen")

    if not name or not phone:
        return jsonify({"error": "Name and phone are required"}), 400

    # Get last user question from bot.py's internal history
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

    # Send email (failure is OK — lead is already saved)
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

# ── Route: Clear Session ───────────────────────────────────────────────────────

@app.route("/clear/<session_id>", methods=["DELETE"])
def clear_session(session_id):
    """Clears conversation history for a session."""
    clear_history(session_id)  # calls bot.py's clear_history()
    return jsonify({"message": f"Session {session_id} cleared."})

# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)