import os
import json
import time
import base64
import random
import requests
import threading
from flask import Flask
from datetime import datetime
from groq import Groq
import fal_client

# ──_keys──────────────────────────────────────────────────────
GEMINI_API_KEY   = "AIzaSyBA14PPwzDH60Rbo_ngnR7i-luoKixh2P8"  # Not used anymore
GROQ_API_KEY     = "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"
TELEGRAM_TOKEN   = "8733495512:AAHHQLMqJdgNpmWTQoofyP9JDn3Os9be1RM"
TELEGRAM_CHAT_ID = "7883707638"
FAL_API_KEY      = "670e2096-81b4-4d42-83f7-a05d09356c16:1b0e490a80f48e56a39b1fbefae614e8"
JSON2VIDEO_KEY   = "PdatZmLXSTdgeUQFfc9GYfuAsoGiDYO8cB2tG4Ax"  # We now use FAL for video too
RENDER_URL       = "https://lanxgrow-social-media-bot.onrender.com/"

os.environ["FAL_KEY"] = FAL_API_KEY
os.environ["FAL_API_KEY"] = FAL_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)

# ── Flask (Render port binding) ───────────────────────────────
app = Flask(__name__)

@app.get("/")
def home():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)

# ── Keep Alive (prevents Render from sleeping) ────────────────
def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
            print("✅ Keep-alive ping sent")
        except Exception as e:
            print(f"Keep-alive error: {e}")
        time.sleep(240)  # ping every 4 minutes

# ── Global State ──────────────────────────────────────────────
LAST_POST = None

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

# ── Quality Checker ───────────────────────────────────────────
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
    global LAST_POST
    send_telegram(f"🔍 Researching + drafting post on: *{topic}*")
    best_post = None
    best_score = 0
    quality = ""

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

    LAST_POST = {
        "topic": topic,
        "post": best_post,
        "score": best_score,
        "quality": quality,
        "timestamp": datetime.now().isoformat()
    }

    return best_post, best_score, quality

# ── Generate Image using FAL.AI (FIXED) ───────────────────────
def generate_image(prompt):
    try:
        print(f"🖼 Generating image with prompt: {prompt[:60]}...")
        result = fal_client.subscribe(
            "fal-ai/flux/dev",
            arguments={
                "prompt": f"Professional Instagram thumbnail for English learning in India: {prompt}. Vibrant, modern, 16:9, realistic, high detail, Indian students, classroom or urban setting.",
                "num_inference_steps": 30,
                "guidance_scale": 3.5,
                "image_size": "square"
            },
            with_logs=True,
        )
        if 'images' in result and len(result['images']) > 0:
            image_url = result['images'][0]['url']
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code == 200:
                return image_response.content
        print("❌ FAL image generation failed: no image returned")
        return None
    except Exception as e:
        print(f"FAL image error: {e}")
        return None

# ── Generate Video using FAL.AI (FIXED) ───────────────────────
def generate_video(prompt):
    try:
        print(f"🎬 Generating video with prompt: {prompt[:60]}...")
        result = fal_client.subscribe(
            "fal-ai/fast-lightning-svd",
            arguments={
                "prompt": f"English learning for Indian students: {prompt}. Style: dynamic, YouTube short, 15 seconds, text overlay: 'LanXgrow - Speak Confidently'. Background: vibrant Indian classroom or city street.",
                "image_size": "1080x1920",
                "num_inference_steps": 25,
                "audio": False,
                "fps": 15
            },
            with_logs=True,
        )
        if 'videos' in result and len(result['videos']) > 0:
            video_url = result['videos'][0]['url']
            return video_url
        print("❌ FAL video generation failed: no video returned")
        return "⏳ Video processing failed. Try again."
    except Exception as e:
        print(f"FAL video error: {e}")
        return f"Video error: {e}"

# ── Send Image to Telegram ────────────────────────────────────
def send_image_telegram(image_data, caption=""):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        if isinstance(image_data, bytes):
            files = {"photo": ("image.jpg", image_data, "image/jpeg")}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
            requests.post(url, files=files, data=data, timeout=30)
        else:
            data = {"chat_id": TELEGRAM_CHAT_ID, "photo": image_data, "caption": caption}
            requests.post(url, json=data, timeout=30)
    except Exception as e:
        send_telegram(f"Image send error: {e}")

# ── Load Analytics ────────────────────────────────────────────
def load_analytics():
    try:
        if os.path.exists("analytics.json"):
            with open("analytics.json", "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except:
        pass
    return []

# ── Save Analytics ────────────────────────────────────────────
def save_analytics(data):
    try:
        with open("analytics.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Analytics save error: {e}")

# ── Morning Report ────────────────────────────────────────────
def morning_report():
    today = datetime.now().strftime("%Y-%m-%d")
    topics = [
        "English speaking confidence for Indian students",
        "Why Tier 2/3 city students struggle in interviews",
        "How LanXgrow transforms communication skills in 7 days"
    ]
    topic = random.choice(topics)

    send_telegram(f"🌅 *Good Morning Apoorva!*\n\n📅 Date: {today}\n🔍 Today's Topic: _{topic}_\n\n⏳ Generating your content package...")

    post, score, quality_report = generate_best_post(topic)

    send_telegram("🎨 Generating image...")
    image_prompt = ask_groq(f"Describe a powerful visual image for this post (one line): {post[:200]}")
    image_data = generate_image(image_prompt)

    send_telegram(f"📦 *Today's Content Package*\n\n📊 *Quality Score: {score}/10*\n✅ *POST (Ready to Copy):*\n\n{post}")

    if image_data:
        send_image_telegram(image_data, "🖼 Image for today's post")
    else:
        send_telegram("⚠️ Image generation failed. Try /image manually.")

    send_telegram(f"📋 *Quality Report:*\n{quality_report}\n\n👉 *Your Actions:*\n1. Copy post → Instagram + LinkedIn\n2. `/like` if post is good\n3. `/dislike` if post needs rework\n4. `/video [topic]` to generate a video")

# ── Handle Commands ───────────────────────────────────────────
def handle_message(text):
    text_lower = text.strip().lower()

    if text_lower in ["/start", "/help"]:
        send_telegram("👋 *LanXgrow AI Agent*\n\nCommands:\n`/morning` — Get today's content package\n`/post [topic]` — Generate post on custom topic\n`/image [prompt]` — Generate image\n`/video [prompt]` — Generate 15s video\n`/like` — Mark last post as LIKED ✅\n`/dislike` — Mark last post as DISLIKED ⚠️\n`/analytics` — See learning report\n`/help` — All commands")

    elif text_lower == "/morning":
        morning_report()

    elif text_lower.startswith("/post"):
        parts = text.split(" ", 1)
        topic = parts[1] if len(parts) > 1 else "English communication skills India"
        post, score, quality = generate_best_post(topic)
        send_telegram(f"📝 *Post (Score: {score}/10):*\n\n{post}")

    elif text_lower.startswith("/image"):
        parts = text.split(" ", 1)
        prompt = parts[1] if len(parts) > 1 else "Indian student speaking confidently"
        send_telegram("🎨 Generating image...")
        image_data = generate_image(prompt)
        if image_data:
            send_image_telegram(image_data, f"🖼 {prompt}")
        else:
            send_telegram("❌ Image generation failed. Try again.")

    elif text_lower.startswith("/video"):
        parts = text.split(" ", 1)
        prompt = parts[1] if len(parts) > 1 else "English learning India"
        send_telegram(f"🎬 Generating video: _{prompt}_\n⏳ Takes ~1-2 minutes...")
        video_url = generate_video(prompt)
        send_telegram(f"📹 *Your Video:*\n{video_url}")

    elif text_lower == "/like":
        if LAST_POST:
            send_telegram(f"✅ *Liked!*\nTopic: {LAST_POST['topic']}\nScore: {LAST_POST['score']}/10\nSaved to analytics!")
            analytics = load_analytics()
            entry = dict(LAST_POST)
            entry['rating'] = 'LIKE'
            analytics.append(entry)
            save_analytics(analytics)
        else:
            send_telegram("❌ No post to rate yet. Use `/morning` or `/post` first.")

    elif text_lower == "/dislike":
        if LAST_POST:
            send_telegram(f"⚠️ *Disliked!*\nTopic: {LAST_POST['topic']}\nScore: {LAST_POST['score']}/10\nSaved. I'll improve!")
            analytics = load_analytics()
            entry = dict(LAST_POST)
            entry['rating'] = 'DISLIKE'
            analytics.append(entry)
            save_analytics(analytics)
        else:
            send_telegram("❌ No post to rate yet. Use `/morning` or `/post` first.")

    elif text_lower == "/analytics":
        analytics = load_analytics()
        if analytics:
            last7 = analytics[-7:]
            lines = []
            for a in last7:
                rating = a.get('rating', 'UNRATED')
                score = a.get('score', 0)
                topic = a.get('topic', 'Unknown')[:40]
                lines.append(f"{'✅' if rating == 'LIKE' else '⚠️' if rating == 'DISLIKE' else '—'} {topic} | Score: {score}/10")
            report = "\n".join(lines)
            send_telegram(f"📊 *Last {len(last7)} Posts:*\n\n{report}")
        else:
            send_telegram("📊 No analytics yet. Generate posts and rate them!")

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

# ── Main Bot Loop ─────────────────────────────────────────────
def run_bot():
    print("🤖 LanXgrow AI Agent LIVE!")
    send_telegram("🟢 *LanXgrow AI Agent is LIVE!*\n\nType `/morning` to get today's content package or `/help` for all commands.")

    offset = None
    last_morning_report = None

    while True:
        try:
            now = datetime.utcnow()
            today = now.strftime("%Y-%m-%d")
            if now.hour == 2 and now.minute < 5 and last_morning_report != today:
                morning_report()
                last_morning_report = today

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

# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    time.sleep(1)

    ping_thread = threading.Thread(target=keep_alive, daemon=True)
    ping_thread.start()

    run_web()
