import os
import json
import time
import base64
import random
import requests
import threading
from flask import Flask
from datetime import datetime, date
from groq import Groq

# =========================
# REQUIRED ENV VARIABLES
# =========================
# Render Environment (DO NOT hardcode keys in code)
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
JSON2VIDEO_KEY   = os.environ.get("JSON2VIDEO_KEY", "")
RENDER_URL       = os.environ.get("RENDER_URL", "https://lanxgrow-social-media-bot.onrender.com/")
GOOGLE_SHEETS_WEBAPP_URL = os.environ.get(
    "GOOGLE_SHEETS_WEBAPP_URL",
    "https://script.google.com/macros/s/AKfycbyIvOVATP3hctm0ZoGuG05hlR4wl-rvT4TRz0NQyw34ZhwQgmW8TdB1W9vPJNOTSUIGLg/exec"
)

# Groq expiry (update in Render when renewed)
GROQ_EXPIRY_DATE = os.environ.get("GROQ_EXPIRY_DATE", "2026-03-30")

# =========================
# INIT
# =========================
groq_client = Groq(api_key=GROQ_API_KEY)

app = Flask(__name__)

@app.get("/")
def home():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)

def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
            print("✅ Keep-alive ping sent")
        except Exception as e:
            print(f"Keep-alive error: {e}")
        time.sleep(240)

LAST_POST = None

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
Competitors: {BRAND_MEMORY['competitors']}

Your jobs:
1. Research competitors and find viral content patterns
2. Create deeply researched, structured social media posts
3. Self-verify quality (score 1-10) — only send 9+ posts
4. Learn from analytics and feedback — improve with every post
5. Generate SEO-rich content with trending keywords
6. Suggest image and video prompts with every post

Never be generic. Always be sharp, data-driven, emotionally resonant.
Focus only on educational content for English communication skills.
"""

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_image_telegram(image_bytes, caption=""):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {"photo": ("image.jpg", image_bytes, "image/jpeg")}
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        requests.post(url, files=files, data=data, timeout=30)
    except Exception as e:
        print(f"Send image error: {e}")

# =========================
# GOOGLE SHEETS via APPS SCRIPT
# =========================
def sheets_post(payload):
    try:
        r = requests.post(
            GOOGLE_SHEETS_WEBAPP_URL,
            json=payload,
            timeout=20
        )
        try:
            return r.json()
        except:
            return {"status": "error", "http": r.status_code, "text": r.text[:300]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def log_post_to_sheet(post_data):
    resp = sheets_post({"action": "log_post", **post_data})
    if resp.get("status") != "ok":
        print("Sheets log_post failed:", resp)

def update_rating_in_sheet(topic, rating):
    resp = sheets_post({"action": "update_rating", "topic": topic, "rating": rating})
    if resp.get("status") != "ok":
        print("Sheets update_rating failed:", resp)

def log_feedback_to_sheet(feedback_text):
    resp = sheets_post({
        "action": "log_feedback",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "feedback_text": feedback_text
    })
    if resp.get("status") != "ok":
        print("Sheets log_feedback failed:", resp)

def read_feedback_for_learning():
    resp = sheets_post({"action": "read_feedback"})
    if resp.get("status") != "ok":
        print("Sheets read_feedback failed:", resp)
        return ""
    return resp.get("feedback", "") or ""

def update_expiry_in_sheet(api_name, days_left, last_reminder):
    resp = sheets_post({
        "action": "update_expiry",
        "api_name": api_name,
        "days_left": days_left,
        "last_reminder": last_reminder
    })
    if resp.get("status") != "ok":
        print("Sheets update_expiry failed:", resp)

# =========================
# GROQ / CONTENT
# =========================
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

def quality_check(post_text):
    score_prompt = f"""
Score this social media post strictly (1-10) for LanXgrow:

POST:
{post_text}

Reply in this exact format:
SCORE: X.X/10
VERDICT: [APPROVE/REWORK]
REASON: [One line]
"""
    return ask_groq(score_prompt)

def research_topic(topic):
    return ask_groq(f"""
Research for a LanXgrow post about: {topic}

Reply EXACTLY:
SOURCES: [...]
CONTENT_TYPES: [...]
QUANTITY: ...
SEO_KEYWORDS: [...]
TRENDING: Yes/No - reason
COMPETITOR_PATTERN: ...
HOOK_TYPE: Question/3 Mistakes/Before-After/Shocking Stat
ENGAGEMENT_PREDICTION: High/Medium/Low
WHAT_LEARNED: ...
""")

def parse_kv(text):
    out = {}
    for line in text.split('\n'):   # ✅ FIXED
        if ':' in line:
            k, _, v = line.partition(':')
            out[k.strip()] = v.strip()
    return out

def generate_best_post(topic, command_used="/post"):
    global LAST_POST

    send_telegram(f"🔍 Researching: *{topic}*")

    research_raw = research_topic(topic)
    research = parse_kv(research_raw)

    feedback = read_feedback_for_learning()
    feedback_context = f"\n\nApply this feedback:\n{feedback}" if feedback else ""

    best_post, best_score, best_quality = None, 0, ""

    for attempt in range(1, 4):
        draft = ask_groq(f"""
Write a viral Instagram/LinkedIn post for LanXgrow about: {topic}

Use:
- SEO Keywords: {research.get('SEO_KEYWORDS','')}
- Hook type: {research.get('HOOK_TYPE','Question')}
- Competitor pattern: {research.get('COMPETITOR_PATTERN','')}
- Trending: {research.get('TRENDING','No')}
- What learned: {research.get('WHAT_LEARNED','')}

Must include CTA: DM SPEAK for free trial
Educational content only.{feedback_context}
""")

        q = quality_check(draft)

        # ✅ FIXED: split('\n')
        try:
            score_line = [l for l in q.split('\n') if 'SCORE:' in l][0]
            score = float(score_line.split(':', 1)[1].strip().split('/')[0])
        except:
            score = 0

        if score > best_score:
            best_score, best_post, best_quality = score, draft, q

        if score >= 9.0:
            break

    image_prompt = ask_groq(f"Give ONE line image prompt based on this post:\n{best_post[:300]}")
    video_prompt = ask_groq(f"Give ONE line 15-sec video prompt based on this post:\n{best_post[:300]}")

    LAST_POST = {
        "topic": topic,
        "post": best_post,
        "score": best_score,
        "quality": best_quality,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "image_prompt": image_prompt,
        "video_prompt": video_prompt,
        "research": research,
        "command_used": command_used
    }

    # Log to sheet (Posts A→T)
    log_post_to_sheet({
        "timestamp": LAST_POST["timestamp"],
        "topic": topic,
        "post_content": best_post,
        "quality_score": best_score,
        "rating": "UNRATED",
        "hook_type_used": research.get("HOOK_TYPE", ""),
        "engagement_prediction": research.get("ENGAGEMENT_PREDICTION", ""),
        "research_sources": research.get("SOURCES", ""),
        "research_content_types": research.get("CONTENT_TYPES", ""),
        "research_quantity": research.get("QUANTITY", ""),
        "what_bot_learned": research.get("WHAT_LEARNED", ""),
        "improvement_applied": "Applied feedback" if feedback else "No feedback yet",
        "image_prompt": image_prompt,
        "video_prompt": video_prompt,
        "seo_keywords": research.get("SEO_KEYWORDS", ""),
        "trending_topic": research.get("TRENDING", ""),
        "competitor_pattern": research.get("COMPETITOR_PATTERN", ""),
        "image_url": "",
        "video_url": "",
        "command_used": command_used
    })

    return best_post, best_score, best_quality

# =========================
# GEMINI IMAGE
# =========================
def generate_image(prompt):
    try:
        # ✅ FIXED model name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": f"Professional Instagram thumbnail (16:9), premium look, for India: {prompt}"}]
            }],
            "generationConfig": {"responseModalities": ["image", "text"]}
        }
        r = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=45)
        j = r.json()
        if "candidates" in j:
            parts = j["candidates"][0]["content"]["parts"]
            for p in parts:
                if "inline_data" in p:
                    return base64.b64decode(p["inline_data"]["data"])
        return None
    except Exception as e:
        print("Gemini image error:", e)
        return None

# =========================
# JSON2VIDEO (basic)
# =========================
def generate_video(prompt):
    try:
        r = requests.post(
            "https://api.json2video.com/v2/videos",
            headers={"Authorization": f"Bearer {JSON2VIDEO_KEY}", "Content-Type": "application/json"},
            json={
                "project": "default",
                "duration": 15,
                "elements": [{
                    "type": "text",
                    "text": f"LanXgrow: {prompt}",
                    "duration": 15,
                    "style": {"font_size": 48, "color": "#ffffff", "background": "#111827"}
                }]
            },
            timeout=90
        )
        return r.json().get("url", "⏳ Video processing... check later")
    except Exception as e:
        return f"Video error: {e}"

# =========================
# EXPIRY REMINDER
# =========================
def check_api_expiry():
    try:
        today = date.today()
        expiry = date.fromisoformat(GROQ_EXPIRY_DATE)
        days_left = (expiry - today).days

        # update sheet tab
        update_expiry_in_sheet("Groq API", days_left, today.strftime("%Y-%m-%d"))

        # remind 10 days before, Mon/Wed/Fri
        if days_left <= 10 and today.weekday() in [0, 2, 4]:
            send_telegram(
                f"⚠️ *Groq API Expiry Reminder*\n\n"
                f"Expires in *{days_left} days*\n"
                f"Expiry date: {GROQ_EXPIRY_DATE}\n"
                f"Renew: https://console.groq.com/keys"
            )
    except Exception as e:
        print("Expiry check error:", e)

# =========================
# TELEGRAM UPDATES LOOP
# =========================
def get_updates(offset=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {"timeout": 30, "offset": offset}
        r = requests.get(url, params=params, timeout=35)
        return r.json()
    except Exception as e:
        print("Update error:", e)
        return {}

def morning_report():
    topics = [
        "English speaking confidence for Indian students",
        "Why Tier 2/3 city students struggle in interviews",
        "How to speak fluently without grammar fear"
    ]
    topic = random.choice(topics)

    send_telegram(f"🌅 *Good Morning!*\n\nTopic: _{topic}_\n\nGenerating…")
    post, score, quality = generate_best_post(topic, command_used="/morning")

    send_telegram(f"📦 *Post (Score: {score}/10)*\n\n{post}")

    send_telegram("🎨 Generating image…")
    img = generate_image(LAST_POST.get("image_prompt", topic))
    if img:
        send_image_telegram(img, "🖼 Image for your post")
    else:
        send_telegram("⚠️ Image failed.")

    check_api_expiry()

def handle_message(text):
    t = text.strip()
    tl = t.lower()

    if tl in ["/start", "/help"]:
        send_telegram(
            "Commands:\n"
            "/morning\n"
            "/post <topic>\n"
            "/image <prompt>\n"
            "/video <prompt>\n"
            "/like\n"
            "/dislike\n"
            "/feedback <text>"
        )
        return

    if tl == "/morning":
        morning_report()
        return

    if tl.startswith("/post"):
        topic = t.split(" ", 1)[1] if " " in t else "English communication skills India"
        post, score, _ = generate_best_post(topic, command_used="/post")
        send_telegram(
            f"📝 *Post (Score: {score}/10)*\n\n{post}\n\n"
            f"🎨 Image Prompt:\n_{LAST_POST.get('image_prompt','')}_\n\n"
            f"🎬 Video Prompt:\n_{LAST_POST.get('video_prompt','')}_"
        )
        return

    if tl.startswith("/feedback"):
        if " " not in t:
            send_telegram("Use: /feedback <your feedback text>")
            return
        fb = t.split(" ", 1)[1]
        log_feedback_to_sheet(fb)
        send_telegram("✅ Feedback saved in sheet.")
        return

    if tl == "/like":
        if not LAST_POST:
            send_telegram("No post yet. Use /post or /morning first.")
            return
        update_rating_in_sheet(LAST_POST["topic"], "LIKE")
        send_telegram("✅ Marked LIKE in sheet.")
        return

    if tl == "/dislike":
        if not LAST_POST:
            send_telegram("No post yet. Use /post or /morning first.")
            return
        update_rating_in_sheet(LAST_POST["topic"], "DISLIKE")
        send_telegram("⚠️ Marked DISLIKE in sheet.")
        return

    if tl.startswith("/image"):
        prompt = t.split(" ", 1)[1] if " " in t else "Indian student speaking confidently"
        img = generate_image(prompt)
        if img:
            send_image_telegram(img, f"🖼 {prompt}")
        else:
            send_telegram("❌ Image failed.")
        return

    if tl.startswith("/video"):
        prompt = t.split(" ", 1)[1] if " " in t else "English learning India"
        send_telegram("🎬 Generating video…")
        url = generate_video(prompt)
        send_telegram(f"📹 {url}")
        return

    # fallback chat
    send_telegram(ask_groq(t))

def run_bot():
    print("🤖 LanXgrow AI Agent LIVE!")
    send_telegram("🟢 Bot live. Use /help.")

    offset = None
    last_morning = None
    last_expiry = None

    while True:
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")

            if now.hour == 8 and now.minute < 5 and last_morning != today:
                morning_report()
                last_morning = today

            if now.hour == 9 and now.minute < 5 and last_expiry != today:
                check_api_expiry()
                last_expiry = today

            updates = get_updates(offset)
            if "result" in updates:
                for u in updates["result"]:
                    offset = u["update_id"] + 1
                    if "message" in u:
                        chat_id = str(u["message"]["chat"]["id"])
                        if chat_id != str(TELEGRAM_CHAT_ID):
                            continue
                        msg = u["message"].get("text", "")
                        if msg:
                            handle_message(msg)

            time.sleep(2)
        except Exception as e:
            print("Loop error:", e)
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    run_web()
