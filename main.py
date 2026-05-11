from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()

    if "hello" in user_message or "hey" in user_message:
        response = "Hey 😘 I’m glad you found me. Tell me a little about yourself..."

    elif "how are you" in user_message:
        response = "Better now that you're here 😏"

    elif "looking" in user_message:
        response = "Maybe I am... what kind of connection are you hoping for? 💋"

    else:
        response = "Mmm tell me more 😘"

    await update.message.reply_text(response)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, reply))

print("Bot running...")

app.run_polling()
