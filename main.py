import logging
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz

# ==== CONFIG ====
BOT_TOKEN = "7720306254:AAFzU60b0fAh5Zl91SBg7jw6Pe4M2to-pnk"
CHANNEL_ID = "@IBS_KSA"  # Example: @IbsImplants
TIMEZONE = "Asia/Riyadh"
# ================

logging.basicConfig(level=logging.INFO)
scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.start()

posts = []


# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "Hello! 👋\nUse /addpost to schedule a post.\nFormat:\n/date YYYY-MM-DD HH:MM\n/message your text or media caption."
  )


async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "Please send your post in this format:\n\n📅 Date and time first:\n/date YYYY-MM-DD HH:MM\n📝 Then your message:\n/message your text"
  )


async def date(update: Update, context: ContextTypes.DEFAULT_TYPE):
  context.user_data["date"] = update.message.text.replace("/date", "").strip()
  await update.message.reply_text(
      "Got it. Now send the message text using /message")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = update.message.text.replace("/message", "").strip()
  date_str = context.user_data.get("date")
  if not date_str:
    await update.message.reply_text("Please use /date first.")
    return

  try:
    tz = pytz.timezone(TIMEZONE)
    dt = tz.localize(datetime.strptime(date_str, "%Y-%m-%d %H:%M"))
    posts.append({"datetime": dt, "text": text})
    scheduler.add_job(send_post, 'date', run_date=dt, args=[text])
    await update.message.reply_text(f"✅ Scheduled post on {dt}")
  except Exception as e:
    await update.message.reply_text(f"Error: {e}")


async def send_post(text):
  bot = Bot(token=BOT_TOKEN)
  await bot.send_message(chat_id=CHANNEL_ID, text=text)


# --- Main ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addpost", addpost))
app.add_handler(CommandHandler("date", date))
app.add_handler(CommandHandler("message", message))

print("Bot running...")
app.run_polling()
