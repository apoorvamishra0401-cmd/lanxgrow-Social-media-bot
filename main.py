# Render redeploy fix - Feb 28 2026
import os
import json
import time
import requests
import threading
from flask import Flask
from datetime import datetime
import fal_client
from groq import Groq

# ── Keys (loaded from Render environment — SAFE) ──────────────
GEMINI_API_KEY   = "AIzaSyBA14PPwzDH60Rbo_ngnR7i-luoKixh2P8"
GROQ_API_KEY     = "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"
TELEGRAM_TOKEN   = "8733495512:AAHHQLMqJdgNpmWTQoofyP9JDn3Os9be1RM"
TELEGRAM_CHAT_ID = "7883707638"
FAL_API_KEY      = "670e2096-81b4-4d42-83f7-a05d09356c16:1b0e490a80f48e56a39b1fbefae614e8"

os.environ["FAL_KEY"] = FAL_API_KEY
os.environ["FAL_API_KEY"] = FAL_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)

# --- Render port binding (required for Web Service) ---
app = Flask(__name__)

@app.get("/")
def home():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

# ── Brand Memory ──────────────────────────────────────────────
BRAND_MEMORY = {
    "company": "LanXgrow",
    "product": "English communication skills for students and professionals",
    "audience": "Indian parents of Grade 5-10, school decision-makers, Tier 2/3 city career aspirants",
    "tone": "Sharp, authoritative, emotionally resonant",
    "best_hooks": ["3 mistakes", "before/after", "shocking stat", "question"],
    "avoid": ["generic motivation", "copy-paste quotes"],
    "cta": "DM SPEAK for free trial",
    "competitors": ["Unacademy", "PhysicsWallah", "BYJU'S", "Vedantu", "EnglishHelper"]
}

SYSTEM_PROMPT = f"""
You are LanXgrow's AI Social Media Manager.

Company: {BRAND_MEMORY['company']}
Product: {BRAND_MEMORY['product']}
Target Audience: {BRAND_MEMORY['audience']}
Tone: {BRAND_MEMORY['tone']}
Best Hooks: {BRAND_MEMORY['best_hooks']}
Avoid: {BRAND_MEMORY['avoid']}
CTA: {BRAND_MEMORY['cta']}

Your jobs:
1. Research competitors and find viral content patterns
2. Create deeply researched, structured social media posts
3. Self-verify quality (score 1-10) — only send 9+ posts
4. Learn from analytics — what worked yesterday improves today
5. Generate image/video prompts for Fal.ai

Never be generic. Always be sharp, data-driven, emotionally resonant.
"""

# ── Send Telegram ─────────────────────────────────────────────
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ── Ask Groq AI ───────────────────────────────────────────────
def ask_groq(prompt):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# ── Quality Checker (Self-Verify) ─────────────────────────────
def quality_check(post_text):
    score_prompt = f"""
Score this social media post strictly (1-10) for LanXgrow:

POST:
{post_text}

Score on ALL 4 criteria:
1. Hook Strength (0-2.5): Does it stop scrolling?
2. Brand Alignment (0-2.5): Matches LanXgrow voice?
3. Engagement Potential (0-2.5): Will Indians comment/share?
4. CTA Clarity (0-2.5): Clear next step?

Reply in this exact format:
SCORE: X.X/10
HOOK: X.X
BRAND: X.X
ENGAGEMENT: X.X
CTA: X.X
VERDICT: [APPROVE/REWORK]
REASON: [One line why]
"""
    return ask_groq(score_prompt)

# ── Generate Post (3 attempts, best wins) ────────────────────
def generate_best_post(topic):
    send_telegram(f"🔍 Researching + drafting post on: *{topic}*")
    best_post = None
    best_score = 0

    for attempt in range(1, 4):
        draft = ask_groq(f"""
Write a viral Instagram/LinkedIn post for LanXgrow about: {topic}

Research angle: How do top edtech companies (Unacademy, PhysicsWallah) approach this topic?
LanXgrow angle: How does this connect to English communication skills for Tier 2/3 India?

Format:
- Hook (first line — stops scroll)
- Value (2-3 lines — insight/story)
- LanXgrow connection (1 line)
- CTA: DM SPEAK for free trial
- Hashtags (5-7 relevant)

Make it sharp, emotional, real. Not generic.
""")

        quality = quality_check(draft)
        print(f"Attempt {attempt}:\n{quality}\n")

        # Extract score
        try:
            score_line = [l for l in quality.split('\n') if 'SCORE:' in l][0]
            score = float(score_line.split(':')[1].strip().split('/')[0])
        except:
            score = 0

        if score > best_score:
            best_score = score
            best_post = draft

        if score >= 9.0:
            break

    return best_post, best_score, quality

# ── Generate Image via Fal.ai ─────────────────────────────────
def generate_image(prompt):
    try:
        result = fal_client.subscribe(
            "fal-ai/flux/dev",
            arguments={
                "prompt": f"Professional, high-quality: {prompt}. Indian context, vibrant, modern.",
                "image_size": "landscape_4_3",
                "num_inference_steps": 28,
                "num_images": 1
            }
        )
        return result["images"][0]["url"]
    except Exception as e:
        return f"Image error: {e}"

# ── Send Image to Telegram ────────────────────────────────────
def send_image_telegram(image_url, caption=""):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        data = {"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": caption}
        requests.post(url, json=data, timeout=30)
    except Exception as e:
        send_telegram(f"Image send error: {e}")

# ── Load Analytics Memory ─────────────────────────────────────
def load_analytics():
    try:
        if os.path.exists("analytics.json"):
            with open("analytics.json", "r") as f:
                return json.load(f)
    except:
        pass
    return {}

# ── Save Analytics Memory ─────────────────────────────────────
def save_analytics(data):
    try:
        with open("analytics.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Analytics save error: {e}")

# ── Morning Report ────────────────────────────────────────────
def morning_report():
    analytics = load_analytics()
    today = datetime.now().strftime("%Y-%m-%d")

    topics = [
        "English speaking confidence for Indian students",
        "Why Tier 2/3 city students struggle in interviews",
        "How LanXgrow transforms communication skills in 7 days"
    ]

    import random
    topic = random.choice(topics)

    send_telegram(f"🌅 *Good Morning Apoorva!*\n\n📅 Date: {today}\n🔍 Today's Topic: _{topic}_\n\n⏳ Generating your content package...")

    # Generate post
    post, score, quality_report = generate_best_post(topic)

    # Generate image
    send_telegram("🎨 Generating image...")
    image_prompt = ask_groq(f"Describe a powerful visual image for this post (one line): {post[:200]}")
    image_url = generate_image(image_prompt)

    # Send full package
    send_telegram(f"""
📦 *Today's Content Package*

📊 *Quality Score: {score}/10*
✅ *POST (Ready to Copy):*

{post}
""")

    if "http" in str(image_url):
        send_image_telegram(image_url, f"🖼 Image for today's post")

    send_telegram(f"""
📋 *Quality Report:*
{quality_report}

👉 *Your Action:*
1. Copy post above
2. Post to Instagram + LinkedIn
3. Reply with today's likes/comments for learning
""")

# ── Handle Telegram Commands ──────────────────────────────────
def handle_message(text):
    text = text.strip().lower()

    if text == "/start" or text == "/help":
        send_telegram("""
👋 *LanXgrow AI Agent*

Commands:
`/morning` — Get today's content package
`/post [topic]` — Generate post on custom topic
`/image [prompt]` — Generate image
`/analytics` — See learning report
`/help` — All commands
""")

    elif text == "/morning":
        morning_report()

    elif text.startswith("/post"):
        parts = text.split(" ", 1)
        topic = parts[1] if len(parts) > 1 else "English communication skills India"
        post, score, quality = generate_best_post(topic)
        send_telegram(f"📝 *Post (Score: {score}/10):*\n\n{post}")

    elif text.startswith("/image"):
        parts = text.split(" ", 1)
        prompt = parts[1] if len(parts) > 1 else "Indian student speaking confidently"
        send_telegram("🎨 Generating image...")
        url = generate_image(prompt)
        if "http" in str(url):
            send_image_telegram(url, f"🖼 {prompt}")
        else:
            send_telegram(url)

    elif text == "/analytics":
        analytics = load_analytics()
        if analytics:
            report = "\n".join([f"📅 {k}: {v}" for k, v in list(analytics.items())[-7:]])
            send_telegram(f"📊 *Last 7 Days Analytics:*\n\n{report}")
        else:
            send_telegram("📊 No analytics yet. Post content and reply with likes/comments!")

    else:
        reply = ask_groq(text)
        send_telegram(reply)

# ── Get Telegram Updates ──────────────────────────────────────
def get_updates(offset=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {"timeout": 30, "offset": offset}
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except Exception as e:
        print(f"Update error: {e}")
        return {}

# ── Main Loop ─────────────────────────────────────────────────
def run_bot():
    print("🤖 LanXgrow AI Agent LIVE!")
    send_telegram("🟢 *LanXgrow AI Agent is LIVE!*\n\nType `/morning` to get today's content package or `/help` for all commands.")

    offset = None
    last_morning_report = None

    while True:
        try:
            # Auto morning report at 8 AM IST (2:30 AM UTC)
            now = datetime.utcnow()
            today = now.strftime("%Y-%m-%d")
            if now.hour == 2 and now.minute < 5 and last_morning_report != today:
                morning_report()
                last_morning_report = today

            # Check Telegram messages
            updates = get_updates(offset)
            if "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        chat_id = str(update["message"]["chat"]["id"])
                        text = update["message"].get("text", "")
                        if chat_id != TELEGRAM_CHAT_ID:
                            continue
                        if text:
                            print(f"📩 {text}")
                            handle_message(text)

            time.sleep(2)

        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    run_web()
