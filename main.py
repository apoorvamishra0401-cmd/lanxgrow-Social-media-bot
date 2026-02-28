# LanXgrow Social Media Bot - Fixed version
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

# ── Keys (use environment variables for security, fallback to defaults) ──
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "AIzaSyBA14PPwzDH60Rbo_ngnR7i-luoKixh2P8")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "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")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "8733495512:AAHHQLMqJdgNpmWTQoofyP9JDn3Os9be1RM")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7883707638")
JSON2VIDEO_KEY   = os.environ.get("JSON2VIDEO_KEY", "PdatZmLXSTdgeUQFfc9GYfuAsoGiDYO8cB2tG4Ax")
RENDER_URL       = os.environ.get("RENDER_URL", "https://lanxgrow-social-media-bot.onrender.com/")

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
            print("Keep-alive ping sent")
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
3. Self-verify quality (score 1-10) -- only send 9+ posts
4. Learn from analytics -- what worked yesterday improves today
5. Generate image/video prompts

Never be generic. Always be sharp, data-driven, emotionally resonant.
"""

# ── Send Telegram ─────────────────────────────────────────────
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f"Telegram send error: {resp.status_code} {resp.text}")
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
        print(f"Groq error: {e}")
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
    send_telegram(f"Researching + drafting post on: *{topic}*")
    best_post = None
    best_score = 0
    quality = ""

    for attempt in range(1, 4):
        draft = ask_groq(f"""
Write a viral Instagram/LinkedIn post for LanXgrow about: {topic}

Research angle: How do top edtech companies (Unacademy, PhysicsWallah) approach this topic?
LanXgrow angle: How does this connect to English communication skills for Tier 2/3 India?

Format:
- Hook (first line -- stops scroll)
- Value (2-3 lines -- insight/story)
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
        except Exception:
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

# ── Generate Image (Gemini) ───────────────────────────────────
# BUG FIX #1: Use correct Gemini model for image generation.
# "gemini-2.0-flash-exp" is DEPRECATED and shut down.
# The correct model for native image generation is "gemini-2.0-flash-exp-image-generation"
# or the newer "gemini-2.5-flash-preview-image-generation".
# We try the newer model first, then fall back to the older one.
def generate_image(prompt):
    # List of models to try in order (newest first)
    models = [
        "gemini-2.0-flash-exp-image-generation",
    ]

    for model_name in models:
        try:
            print(f"Trying image generation with model: {model_name}")
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{"text": f"Generate a professional Instagram thumbnail image for English learning in India: {prompt}. Vibrant, modern, 16:9 aspect ratio."}]
                    }],
                    "generationConfig": {
                        "responseModalities": ["image", "text"],
                        "imageSizeOptions": {
                            "aspectRatio": "LANDSCAPE_16_9"
                        }
                    }
                },
                timeout=60  # BUG FIX #2: Increased timeout from 45s to 60s for image gen
            )

            result = response.json()
            print(f"Gemini response status: {response.status_code}")

            # Check for API errors
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                print(f"Gemini API error with {model_name}: {error_msg}")
                continue  # Try next model

            if "candidates" in result:
                parts = result["candidates"][0]["content"]["parts"]
                for part in parts:
                    if "inlineData" in part:
                        # BUG FIX #3: Gemini API returns "inlineData" (camelCase),
                        # NOT "inline_data" (snake_case). This was a CRITICAL bug
                        # causing image extraction to always fail silently.
                        image_bytes = base64.b64decode(part["inlineData"]["data"])
                        print(f"Image generated successfully with {model_name}! Size: {len(image_bytes)} bytes")
                        return image_bytes
                    elif "inline_data" in part:
                        # Fallback for older API versions that might use snake_case
                        image_bytes = base64.b64decode(part["inline_data"]["data"])
                        print(f"Image generated successfully with {model_name} (legacy format)! Size: {len(image_bytes)} bytes")
                        return image_bytes

                print(f"No image data found in response parts from {model_name}")
            else:
                print(f"No candidates in response from {model_name}: {json.dumps(result)[:500]}")

        except requests.exceptions.Timeout:
            print(f"Timeout with model {model_name}")
            continue
        except Exception as e:
            print(f"Gemini image error with {model_name}: {e}")
            continue

    print("All image generation models failed")
    return None

# ── Generate Video (JSON2Video) ───────────────────────────────
# BUG FIX #4: WRONG ENDPOINT - was using /v2/videos (does NOT exist)
# Correct endpoint is /v2/movies
# BUG FIX #5: WRONG AUTH HEADER - was using "Authorization: Bearer KEY"
# Correct header is "x-api-key: KEY"
# BUG FIX #6: WRONG JSON PAYLOAD STRUCTURE - was using flat "elements" array
# Correct structure requires "scenes" array containing "elements"
def generate_video(prompt):
    try:
        # Step 1: Create the movie rendering job
        response = requests.post(
            "https://api.json2video.com/v2/movies",  # FIX: /movies not /videos
            headers={
                "x-api-key": JSON2VIDEO_KEY,          # FIX: x-api-key not Bearer auth
                "Content-Type": "application/json"
            },
            json={
                "scenes": [{                           # FIX: must be inside "scenes" array
                    "elements": [{
                        "type": "text",
                        "text": f"LanXgrow: {prompt}",
                        "duration": 15,
                        "style": {
                            "font_size": 48,
                            "color": "#ffffff",
                            "background": "#1e3a8a"
                        }
                    }]
                }]
            },
            timeout=90
        )

        result = response.json()
        print(f"JSON2Video create response: {json.dumps(result)[:500]}")

        if not result.get("success"):
            error_msg = result.get("message", "Unknown error from JSON2Video")
            print(f"JSON2Video error: {error_msg}")
            return f"Video creation error: {error_msg}"

        project_id = result.get("project")
        if not project_id:
            return "Video error: No project ID returned"

        # Step 2: Poll for completion (BUG FIX #7: original code never polled)
        # The old code just returned result.get("url") which is NEVER in the create response
        for poll_attempt in range(24):  # Poll for up to ~2 minutes
            time.sleep(5)
            status_resp = requests.get(
                f"https://api.json2video.com/v2/movies?project={project_id}",
                headers={"x-api-key": JSON2VIDEO_KEY},
                timeout=30
            )
            status = status_resp.json()
            movie = status.get("movie", {})
            movie_status = movie.get("status", "unknown")
            print(f"Video poll {poll_attempt + 1}: status={movie_status}")

            if movie_status == "done":
                video_url = movie.get("url", "")
                if video_url:
                    return video_url
                return "Video rendered but no URL returned"
            elif movie_status == "error":
                error_msg = movie.get("message", "Unknown rendering error")
                return f"Video rendering error: {error_msg}"
            # else: still pending/running, keep polling

        return "Video is still processing. It may take a few more minutes. Check back later."

    except Exception as e:
        print(f"Video generation error: {e}")
        return f"Video error: {e}"

# ── Send Image to Telegram ────────────────────────────────────
def send_image_telegram(image_data, caption=""):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        if isinstance(image_data, bytes):
            # BUG FIX #8: Use PNG since Gemini generates PNG images, not JPEG
            files = {"photo": ("image.png", image_data, "image/png")}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
            resp = requests.post(url, files=files, data=data, timeout=30)
            if not resp.ok:
                print(f"Telegram image send error: {resp.status_code} {resp.text}")
                send_telegram(f"Image send failed: {resp.status_code}")
        else:
            data = {"chat_id": TELEGRAM_CHAT_ID, "photo": image_data, "caption": caption}
            resp = requests.post(url, json=data, timeout=30)
            if not resp.ok:
                print(f"Telegram image URL send error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Image send exception: {e}")
        send_telegram(f"Image send error: {e}")

# ── Load Analytics ────────────────────────────────────────────
def load_analytics():
    try:
        if os.path.exists("analytics.json"):
            with open("analytics.json", "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception as e:
        print(f"Analytics load error: {e}")
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

    send_telegram(f"*Good Morning Apoorva!*\n\nDate: {today}\nTopic: _{topic}_\n\nGenerating your content package...")

    post, score, quality_report = generate_best_post(topic)

    send_telegram("Generating image...")
    image_prompt = ask_groq(f"Describe a powerful visual image for this post (one line, be specific about colors, subjects, and composition): {post[:200]}")
    image_data = generate_image(image_prompt)

    send_telegram(f"*Today's Content Package*\n\nQuality Score: {score}/10\n\n*POST (Ready to Copy):*\n\n{post}")

    if image_data:
        send_image_telegram(image_data, "Image for today's post")
    else:
        send_telegram("Image generation failed. Try /image manually.")

    send_telegram(f"*Quality Report:*\n{quality_report}\n\n*Your Actions:*\n1. Copy post to Instagram + LinkedIn\n2. /like if post is good\n3. /dislike if post needs rework\n4. /video [topic] to generate a video")

# ── Handle Commands ───────────────────────────────────────────
def handle_message(text):
    text_lower = text.strip().lower()

    if text_lower in ["/start", "/help"]:
        send_telegram("*LanXgrow AI Agent*\n\nCommands:\n/morning -- Get today's content package\n/post [topic] -- Generate post on custom topic\n/image [prompt] -- Generate image\n/video [prompt] -- Generate 15s video\n/like -- Mark last post as LIKED\n/dislike -- Mark last post as DISLIKED\n/analytics -- See learning report\n/help -- All commands")

    elif text_lower == "/morning":
        morning_report()

    elif text_lower.startswith("/post"):
        parts = text.split(" ", 1)
        topic = parts[1] if len(parts) > 1 else "English communication skills India"
        post, score, quality = generate_best_post(topic)
        send_telegram(f"*Post (Score: {score}/10):*\n\n{post}")

    elif text_lower.startswith("/image"):
        parts = text.split(" ", 1)
        prompt = parts[1] if len(parts) > 1 else "Indian student speaking confidently in a modern classroom"
        send_telegram("Generating image...")
        image_data = generate_image(prompt)
        if image_data:
            send_image_telegram(image_data, f"{prompt}")
        else:
            send_telegram("Image generation failed. The Gemini API may be rate-limited. Please try again in a moment.")

    elif text_lower.startswith("/video"):
        parts = text.split(" ", 1)
        prompt = parts[1] if len(parts) > 1 else "English learning India"
        send_telegram(f"Generating video: _{prompt}_\nThis takes ~2 minutes...")
        video_url = generate_video(prompt)
        send_telegram(f"*Your Video:*\n{video_url}")

    elif text_lower == "/like":
        if LAST_POST:
            send_telegram(f"*Liked!*\nTopic: {LAST_POST['topic']}\nScore: {LAST_POST['score']}/10\nSaved to analytics!")
            analytics = load_analytics()
            entry = dict(LAST_POST)
            entry['rating'] = 'LIKE'
            analytics.append(entry)
            save_analytics(analytics)
        else:
            send_telegram("No post to rate yet. Use /morning or /post first.")

    elif text_lower == "/dislike":
        if LAST_POST:
            send_telegram(f"*Disliked!*\nTopic: {LAST_POST['topic']}\nScore: {LAST_POST['score']}/10\nSaved. I'll improve!")
            analytics = load_analytics()
            entry = dict(LAST_POST)
            entry['rating'] = 'DISLIKE'
            analytics.append(entry)
            save_analytics(analytics)
        else:
            send_telegram("No post to rate yet. Use /morning or /post first.")

    elif text_lower == "/analytics":
        analytics = load_analytics()
        if analytics:
            last7 = analytics[-7:]
            lines = []
            for a in last7:
                rating = a.get('rating', 'UNRATED')
                score = a.get('score', 0)
                topic = a.get('topic', 'Unknown')[:40]
                icon = "+" if rating == 'LIKE' else "-" if rating == 'DISLIKE' else "?"
                lines.append(f"[{icon}] {topic} | Score: {score}/10")
            report = "\n".join(lines)
            send_telegram(f"*Last {len(last7)} Posts:*\n\n{report}")
        else:
            send_telegram("No analytics yet. Generate posts and rate them!")

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
    print("LanXgrow AI Agent LIVE!")
    send_telegram("*LanXgrow AI Agent is LIVE!*\n\nType /morning to get today's content package or /help for all commands.")

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
                            print(f"Received: {text}")
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
