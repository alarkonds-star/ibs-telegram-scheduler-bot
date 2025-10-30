import os
import logging
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

# ==== CONFIG ====
BOT_TOKEN = os.getenv("BOT_TOKEN")  # secure token from Render
CHANNEL_ID = "@IBS_KSA"             # your channel username
TIMEZONE = "Asia/Riyadh"
# ================

logging.basicConfig(level=logging.INFO)
scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.start()

posts = []


# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\nUse these commands:\n"
        "/date YYYY-MM-DD HH:MM → set time\n"
        "Then send your post (text, image, video, PDF, or URL) with /message."
    )


async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗓 Please set your date first:\n/date YYYY-MM-DD HH:MM\nThen send your post with /message."
    )


async def date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text.replace("/date", "").strip()
    await update.message.reply_text("✅ Date saved! Now send your message using /message.")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = context.user_data.get("date")
    if not date_str:
        await update.message.reply_text("❗ Please use /date first.")
        return

    # detect what the user sent
    media = None
    caption = update.message.caption or update.message.text.replace("/message", "").strip()

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
        media = file_id
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
        media = file_id
    elif update.message.document:
        file_id = update.message.document.file_id
        media_type = "document"
        media = file_id
    else:
        media_type = "text"

    try:
        tz = pytz.timezone(TIMEZONE)
        dt = tz.localize(datetime.strptime(date_str, "%Y-%m-%d %H:%M"))

        job_data = {"datetime": dt, "media_type": media_type, "media": media, "caption": caption}
        posts.append(job_data)

        scheduler.add_job(send_post, 'date', run_date=dt, args=[job_data])
        await update.message.reply_text(f"✅ Scheduled post on {dt}")
    except Exception as e:
