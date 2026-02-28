import os
import json
import time
import base64
import random
import requests
import threading
from flask import Flask, request
from datetime import datetime
from groq import Groq

# ENV VARIABLES
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RENDER_URL       = os.environ.get("RENDER_URL", "https://lanxgrow-social-media-bot.onrender.com/")

groq_client = Groq(api_key=GROQ_API_KEY)
app = Flask(__name__)

@app.route("/")
def home():
    return "OK", 200

# WEBHOOK (simple)
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if "message" in update:
            chat_id = str(update["message"]["chat"]["id"])
            if chat_id == TELEGRAM_CHAT_ID:
                msg = update["message"].get("text", "")
                handle_message(msg)
        return "OK", 200
    except:
        return "OK", 200

def setup_webhook():
    webhook_url = f"{RENDER_URL.rstrip('/')}/webhook"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    requests.post(url, json={"url": webhook_url})

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage
