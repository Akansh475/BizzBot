"""
config.py — Central settings for BizBot
All configuration values live here so we only change one file,
not hunt through multiple files when something needs updating.
"""

import os
from dotenv import load_dotenv

# Load values from .env file into environment variables
load_dotenv()

# ── AI Settings ────────────────────────────────────────────────────────────────

# Groq API key — stored in .env, never hardcoded here
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# The Groq model we're using (free tier, fast responses)
MODEL_NAME = "llama-3.1-8b-instant"

# How many past messages we send to the AI for context
# Keeping this small saves API tokens and money
MAX_HISTORY = 6

# When the AI says this exact phrase, the frontend shows the lead capture form
HANDOFF_PHRASE = "I'll connect you with the team!"

# ── File Paths ─────────────────────────────────────────────────────────────────

# Folder where business knowledge base .txt files live
BUSINESSES_FOLDER = "businesses"

# Folder where captured leads will be saved as JSON files
LEADS_FOLDER = "leads"

# ── Email Settings ─────────────────────────────────────────────────────────────

# Gmail address that SENDS the notification email
# This is YOUR gmail (or a dedicated Gmail you create for BizBot)
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

# Gmail "App Password" — NOT your normal Gmail password
# You generate this at: myaccount.google.com → Security → App Passwords
# Required because Gmail blocks plain passwords for SMTP
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# Gmail SMTP server address (don't change this)
SMTP_HOST = "smtp.gmail.com"

# Port 587 uses STARTTLS encryption — the standard secure port for Gmail
SMTP_PORT = 587