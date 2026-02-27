# LanXgrow AI Agent - Complete Version Feb 28 2026
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
import fal_client
import gspread
from google.oauth2.service_account import Credentials

# ── Keys ──────────────────────────────────────────────────────
GEMINI_API_KEY   = "AIzaSyBA14PPwzDH60Rbo_ngnR7i-luoKixh2P8"
GROQ_API_KEY     = "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"
TELEGRAM_TOKEN   = "8733495512:AAHHQLMqJdgNpmWTQoofyP9JDn3Os9be1RM"
TELEGRAM_CHAT_ID = "7883707638"
FAL_API_KEY      = "670e2096-81b4-4d42-83f7-a05d09356c16:1b0e490a80f48e56a39b1fbefae614e8"
JSON2VIDEO_KEY   = "PdatZmLXSTdgeUQFfc9GYfuAsoGiDYO8cB2tG4Ax"
RENDER_URL       = "https://lanxgrow-social-media-bot.onrender.com/"
SHEET_NAME       = "LanXgrow Content Analytics"
SHEETS_SCOPES    = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Groq API expiry date - update this when you renew
GROQ_EXPIRY_DATE = "2026-03-30"

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

# ── Keep Alive (UptimeRobot + self-ping) ─────────────────────
def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
            print("✅ Keep-alive ping sent")
        except Exception as e:
            print(f"Keep-alive error: {e}")
        time.sleep(240)

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

# ── Google Sheets Client ──────────────────────────────────────
def get_sheets_client():
    try:
        secret_path = "/etc/secrets/google_service_account.json"
        if not os.path.exists(secret_path):
            print("⚠️ Google Sheets secret file not found:", secret_path)
            return None

        with open(secret_path, "r") as f:
            info = json.load(f)

        creds = Credentials.from_service_account_info(info, scopes=SHEETS_SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Sheets auth error: {e}")
        return None
    try:
        cred_json = os.environ.get("GOOGLE_SHEETS_CRED_JSON")
        if not cred_json:
            print("⚠️ No Google Sheets credentials in environment.")
            return None
        info = json.loads(cred_json)
        creds = Credentials.from_service_account_info(info, scopes=SHEETS_SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Sheets auth error: {e}")
        return None

# ── Log Post to Sheet (A→T, 20 columns) ──────────────────────
def log_post_to_sheet(post_data):
    try:
        client = get_sheets_client()
        if not client:
            return
        sheet = client.open(SHEET_NAME).worksheet("Posts")
        row = [
            post_data.get("timestamp", ""),           # A
            post_data.get("topic", ""),                # B
            post_data.get("post_content", ""),         # C
            post_data.get("quality_score", ""),        # D
            post_data.get("rating", "UNRATED"),        # E
            post_data.get("hook_type_used", ""),       # F
            post_data.get("engagement_prediction", ""),# G
            post_data.get("research_sources", ""),     # H
            post_data.get("research_content_types",""),# I
            post_data.get("research_quantity", ""),    # J
            post_data.get("what_bot_learned", ""),     # K
            post_data.get("improvement_applied", ""),  # L
            post_data.get("image_prompt", ""),         # M
            post_data.get("video_prompt", ""),         # N
            post_data.get("seo_keywords", ""),         # O
            post_data.get("trending_topic", ""),       # P
            post_data.get("competitor_pattern", ""),   # Q
            post_data.get("image_url", ""),            # R
            post_data.get("video_url", ""),            # S
            post_data.get("command_used", ""),         # T
        ]
        sheet.append_row(row, value_input_option="RAW")
        print("✅ Post logged to Sheets")
    except Exception as e:
        print(f"Sheets post log error: {e}")

# ── Update Rating in Sheet ────────────────────────────────────
def update_rating_in_sheet(topic, rating):
    try:
        client = get_sheets_client()
        if not client:
            return
        sheet = client.open(SHEET_NAME).worksheet("Posts")
        col_b = sheet.col_values(2)  # Topic column
        for i, val in enumerate(col_b):
            if val == topic:
                sheet.update_cell(i + 1, 5, rating)  # Column E = Rating
                print(f"✅ Rating updated in Sheets: {rating}")
                break
    except Exception as e:
        print(f"Sheets rating update error: {e}")

# ── Log Feedback to Sheet ─────────────────────────────────────
def log_feedback_to_sheet(feedback_text):
    try:
        client = get_sheets_client()
        if not client:
            return
        sheet = client.open(SHEET_NAME).worksheet("Feedback")
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            feedback_text,
            "New",
            ""
        ]
        sheet.append_row(row, value_input_option="RAW")
        print("✅ Feedback logged to Sheets")
    except Exception as e:
        print(f"Sheets feedback log error: {e}")

# ── Read Feedback for Learning ────────────────────────────────
def read_feedback_for_learning():
    try:
        client = get_sheets_client()
        if not client:
            return ""
        sheet = client.open(SHEET_NAME).worksheet("Feedback")
        all_rows = sheet.get_all_records()
        new_feedback = [r for r in all_rows if r.get("Status") == "New"]
        if not new_feedback:
            return ""
        feedback_text = "\n".join([r.get("Feedback Text", "") for r in new_feedback])
        # Mark as Read
        for i, row in enumerate(all_rows):
            if row.get("Status") == "New":
                sheet.update_cell(i + 2, 3, "Read")
        return feedback_text
    except Exception as e:
        print(f"Feedback read error: {e}")
        return ""

# ── Log API Expiry to Sheet ───────────────────────────────────
def update_api_expiry_sheet():
    try:
        client = get_sheets_client()
        if not client:
            return
        sheet = client.open(SHEET_NAME).worksheet("API Expiry")
        today = date.today()
        expiry = date.fromisoformat(GROQ_EXPIRY_DATE)
        days_left = (expiry - today).days
        col_a = sheet.col_values(1)
        for i, val in enumerate(col_a):
            if val == "Groq API":
                sheet.update_cell(i + 1, 3, days_left)
                break
    except Exception as e:
        print(f"API expiry update error: {e}")

# ── Check API Expiry & Send Reminder ─────────────────────────
def check_api_expiry():
    try:
        today = date.today()
        expiry = date.fromisoformat(GROQ_EXPIRY_DATE)
        days_left = (expiry - today).days
        update_api_expiry_sheet()

        # Remind if 10 days or less remaining, Mon/Wed/Fri only
        if days_left <= 10 and today.weekday() in [0, 2, 4]:
            send_telegram(
                f"⚠️ *API Expiry Reminder*\n\n"
                f"🔑 *Groq API* expires in *{days_left} days*\n"
                f"📅 Expiry Date: {GROQ_EXPIRY_DATE}\n\n"
                f"👉 Renew here: https://console.groq.com/keys\n"
                f"After renewing, update `GROQ_API_KEY` in Render Environment Variables."
            )
            print(f"⚠️ Groq expiry reminder sent. {days_left} days left.")
    except Exception as e:
        print(f"Expiry check error: {e}")

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

# ── Research Helper ───────────────────────────────────────────
def research_topic(topic):
    research = ask_groq(f"""
You are researching for a LanXgrow social media post about: {topic}

Do the following:
1. Identify 3-5 educational content sources/angles (e.g. Unacademy blog, PhysicsWallah YouTube style, LinkedIn edtech posts)
2. Extract trending patterns from edtech content in India
3. Find top 5-7 SEO keywords Indians search on Google for this topic
4. Identify if this topic is currently trending (Yes/No) and why
5. Find the best competitor content pattern to adapt
6. Suggest what hook type would work best: Question / 3 Mistakes / Before-After / Shocking Stat
7. Predict engagement level: High / Medium / Low
8. Summarize what you learned in 2 lines

Reply in this EXACT format:
SOURCES: [source1, source2, source3]
CONTENT_TYPES: [Article, Video, Blog Post, etc]
QUANTITY: [approx words/content analyzed]
SEO_KEYWORDS: [keyword1, keyword2, keyword3, keyword4, keyword5]
TRENDING: [Yes/No - reason]
COMPETITOR_PATTERN: [describe pattern]
HOOK_TYPE: [Question/3 Mistakes/Before-After/Shocking Stat]
ENGAGEMENT_PREDICTION: [High/Medium/Low]
WHAT_LEARNED: [2-line summary]
""")
    return research

# ── Parse Research Output ─────────────────────────────────────
def parse_research(research_text):
    result = {}
    for line in research_text.split('\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            result[key.strip()] = value.strip()
    return result

# ── Generate Post (3 attempts, best wins) ────────────────────
def generate_best_post(topic, command_used="/post"):
    global LAST_POST

    send_telegram(f"🔍 Researching: *{topic}*")

    # Step 1: Research
    research_raw = research_topic(topic)
    research = parse_research(research_raw)

    # Step 2: Read feedback for improvement
    feedback = read_feedback_for_learning()
    feedback_context = f"\n\nApply this user feedback to improve the post:\n{feedback}" if feedback else ""

    best_post = None
    best_score = 0
    quality = ""

    for attempt in range(1, 4):
        draft = ask_groq(f"""
Write a viral Instagram/LinkedIn post for LanXgrow about: {topic}

Research Insights:
- SEO Keywords to use naturally: {research.get('SEO_KEYWORDS', '')}
- Best Hook Type: {research.get('HOOK_TYPE', 'Question')}
- Competitor Pattern to adapt: {research.get('COMPETITOR_PATTERN', '')}
- Trending: {research.get('TRENDING', 'No')}
- What I learned: {research.get('WHAT_LEARNED', '')}

Format:
- Hook (first line using {research.get('HOOK_TYPE', 'Question')} style — stops scroll)
- Value (2-3 lines — insight/story/data)
- LanXgrow connection (1 line)
- CTA: DM SPEAK for free trial
- Hashtags (5-7 SEO-rich relevant hashtags)

Rules:
- Use educational content angle only
- Embed SEO keywords naturally
- Make it sharp, emotional, real — not generic
- Focus on career/future outcomes for Indian students{feedback_context}
""")

        quality = quality_check(draft)
        print(f"Attempt {attempt}:\n{quality}\n")

        # ✅ FIXED: was \\n before
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

    # Generate image + video prompts
    image_prompt = ask_groq(f"Describe ONE powerful visual image (one line only) for this post: {best_post[:200]}")
    video_prompt = ask_groq(f"Describe ONE 15-second video concept (one line only) for this post: {best_post[:200]}")

    LAST_POST = {
        "topic": topic,
        "post": best_post,
        "score": best_score,
        "quality": quality,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "image_prompt": image_prompt,
        "video_prompt": video_prompt,
        "research": research,
        "command_used": command_used
    }

    # Log to Google Sheets
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
        "improvement_applied": f"Feedback applied: {feedback[:100]}" if feedback else "No feedback yet",
        "image_prompt": image_prompt,
        "video_prompt": video_prompt,
        "seo_keywords": research.get("SEO_KEYWORDS", ""),
        "trending_topic": research.get("TRENDING", ""),
        "competitor_pattern": research.get("COMPETITOR_PATTERN", ""),
        "image_url": "",
        "video_url": "",
        "command_used": command_used,
    })

    return best_post, best_score, quality

# ── Generate Image (Gemini) ───────────────────────────────────
def generate_image(prompt):
    try:
        # ✅ FIXED: model name corrected
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": f"Professional Instagram thumbnail for English learning in India: {prompt}. Vibrant, modern, 16:9."}]
                }],
                "generationConfig": {"responseModalities": ["image", "text"]}
            },
            timeout=45
        )
        result = response.json()
        if "candidates" in result:
            parts = result["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inline_data" in part:
                    image_bytes = base64.b64decode(part["inline_data"]["data"])
                    return image_bytes
        return None
    except Exception as e:
        print(f"Gemini image error: {e}")
        return None

# ── Generate Video (JSON2Video) ───────────────────────────────
def generate_video(prompt):
    try:
        response = requests.post(
            "https://api.json2video.com/v2/videos",
            headers={
                "Authorization": f"Bearer {JSON2VIDEO_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "project": "default",
                "duration": 15,
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
            },
            timeout=90
        )
        result = response.json()
        return result.get("url", "⏳ Video processing... check in 2 min")
    except Exception as e:
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

# ── Load/Save Analytics ───────────────────────────────────────
def load_analytics():
    try:
        if os.path.exists("analytics.json"):
            with open("analytics.json", "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except:
        pass
    return []

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

    send_telegram(f"🌅 *Good Morning Apoorva!*\n\n📅 Date: {today}\n🔍 Today's Topic: _{topic}_\n\n⏳ Researching + generating your content package...")

    post, score, quality_report = generate_best_post(topic, command_used="/morning")

    send_telegram("🎨 Generating image...")
    image_data = generate_image(LAST_POST.get("image_prompt", topic))

    send_telegram(f"📦 *Today's Content Package*\n\n📊 *Quality Score: {score}/10*\n✅ *POST (Ready to Copy):*\n\n{post}")

    if image_data:
        send_image_telegram(image_data, "🖼 Image for today's post")
    else:
        send_telegram("⚠️ Image generation failed. Try /image manually.")

    send_telegram(
        f"🎨 *Suggested Image Prompt:*\n_{LAST_POST.get('image_prompt', '')}_\n\n"
        f"🎬 *Suggested Video Prompt:*\n_{LAST_POST.get('video_prompt', '')}_\n\n"
        f"📋 *Quality Report:*\n{quality_report}\n\n"
        f"👉 *Your Actions:*\n"
        f"1. Copy post → Instagram + LinkedIn\n"
        f"2. `/like` if post is good ✅\n"
        f"3. `/dislike` if post needs rework ⚠️\n"
        f"4. `/video [topic]` to generate a video 🎬\n"
        f"5. `/feedback [your thoughts]` to improve future posts 💡"
    )

    check_api_expiry()

# ── Handle Commands ───────────────────────────────────────────
def handle_message(text):
    text_lower = text.strip().lower()

    if text_lower in ["/start", "/help"]:
        send_telegram(
            "👋 *LanXgrow AI Agent*\n\n"
            "Commands:\n"
            "`/morning` — Get today's content package\n"
            "`/post [topic]` — Generate post on custom topic\n"
            "`/image [prompt]` — Generate image\n"
            "`/video [prompt]` — Generate 15s video\n"
            "`/like` — Mark last post as LIKED ✅\n"
            "`/dislike` — Mark last post as DISLIKED ⚠️\n"
            "`/feedback [text]` — Give feedback to improve bot 💡\n"
            "`/analytics` — See learning report\n"
            "`/help` — All commands"
        )

    elif text_lower == "/morning":
        morning_report()

    elif text_lower.startswith("/post"):
        parts = text.split(" ", 1)
        topic = parts[1] if len(parts) > 1 else "English communication skills India"
        post, score, quality = generate_best_post(topic, command_used="/post")
        send_telegram(
            f"📝 *Post (Score: {score}/10):*\n\n{post}\n\n"
            f"🎨 *Image Prompt:*\n_{LAST_POST.get('image_prompt', '')}_\n\n"
            f"🎬 *Video Prompt:*\n_{LAST_POST.get('video_prompt', '')}_"
        )

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
        send_telegram(f"🎬 Generating video: _{prompt}_\n⏳ Takes ~2 minutes...")
        video_url = generate_video(prompt)
        send_telegram(f"📹 *Your Video:*\n{video_url}")

    elif text_lower == "/like":
        if LAST_POST:
            send_telegram(f"✅ *Liked!*\nTopic: {LAST_POST['topic']}\nScore: {LAST_POST['score']}/10\nSaved to analytics + Sheet!")
            analytics = load_analytics()
            entry = dict(LAST_POST)
            entry['rating'] = 'LIKE'
            analytics.append(entry)
            save_analytics(analytics)
            update_rating_in_sheet(LAST_POST['topic'], 'LIKE')
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
            update_rating_in_sheet(LAST_POST['topic'], 'DISLIKE')
        else:
            send_telegram("❌ No post to rate yet. Use `/morning` or `/post` first.")

    elif text_lower.startswith("/feedback"):
        parts = text.split(" ", 1)
        if len(parts) > 1:
            feedback_text = parts[1]
            log_feedback_to_sheet(feedback_text)
            send_telegram(f"💡 *Feedback saved!*\n\n_{feedback_text}_\n\nI'll apply this to future posts. Thank you Apoorva! 🙏")
        else:
            send_telegram("❌ Please add your feedback text.\nExample: `/feedback Use more emotional hooks`")

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
    last_expiry_check = None

    while True:
        try:
            now = datetime.utcnow()
            today = now.strftime("%Y-%m-%d")

            # Auto morning report at 8 AM IST (2:30 AM UTC)
            if now.hour == 2 and now.minute < 5 and last_morning_report != today:
                morning_report()
                last_morning_report = today

            # Daily expiry check at 9 AM IST (3:30 AM UTC)
            if now.hour == 3 and now.minute < 5 and last_expiry_check != today:
                check_api_expiry()
                last_expiry_check = today

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
