import os
import logging
from telegram import (
    Bot,
    Update,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

# ==== CONFIG ====
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Loaded securely from Render
CHANNEL_ID = "@IBS_KSA"             # Channel username (must add bot as admin!)
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

    caption = update.message.caption or update.message.text.replace("/message", "").strip()
    media_group = []

    # detect multiple media
    if update.message.photo:
        # handle multiple photos
        for photo in update.message.photo:
            media_group.append(("photo", photo.file_id))
    elif update.message.video:
        media_group.append(("video", update.message.video.file_id))
    elif update.message.document:
        media_group.append(("document", update.message.document.file_id))
    else:
        media_group.append(("text", caption))

    try:
        tz = pytz.timezone(TIMEZONE)
        dt = tz.localize(datetime.strptime(date_str, "%Y-%m-%d %H:%M"))

        job_data = {"datetime": dt, "media_group": media_group, "caption": caption}
        posts.append(job_data)

        scheduler.add_job(send_post, 'date', run_date=dt, args=[job_data])
        await update.message.reply_text(f"✅ Scheduled post on {dt}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def send_post(job_data):
    bot = Bot(token=BOT_TOKEN)
    media_group = job_data["media_group"]
    caption = job_data["caption"]

    try:
        # Multiple photos/videos (album)
        if len(media_group) > 1 and media_group[0][0] in ["photo", "video"]:
            if media_group[0][0] == "photo":
                media = [
                    InputMediaPhoto(m[1], caption=caption if i == 0 else None)
                    for i, m in enumerate(media_group)
                ]
            else:
                media = [
                    InputMediaVideo(m[1], caption=caption if i == 0 else None)
                    for i, m in enumerate(media_group)
                ]
            await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        else:
            # single item
            media_type, media = media_group[0]
            if media_type == "photo":
                await bot.send_photo(chat_id=CHANNEL_ID, photo=media, caption=caption)
            elif media_type == "video":
                await bot.send_video(chat_id=CHANNEL_ID, video=media, caption=caption)
            elif media_type == "document":
                await bot.send_document(chat_id=CHANNEL_ID, document=media, caption=caption)
            else:
                await bot.send_message(chat_id=CHANNEL_ID, text=caption)

        logging.info(f"✅ Sent scheduled post to {CHANNEL_ID}")
    except Exception as e:
        logging.error(f"❌ Error sending post: {e}")


# Optional: list scheduled posts
async def listposts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not posts:
        await update.message.reply_text("📭 No posts scheduled yet.")
        return

    msg = "🗓️ *Scheduled Posts:*\n"
    for i, p in enumerate(posts, start=1):
        msg += f"{i}. {p['datetime'].strftime('%Y-%m-%d %H:%M')} — {p['media_group'][0][0]}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")


# --- Main ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addpost", addpost))
app.add_handler(CommandHandler("date", date))
app.add_handler(CommandHandler("listposts", listposts))
app.add_handler(MessageHandler(filters.COMMAND | filters.ALL, message))

print("🤖 Bot running...")
app.run_polling()
