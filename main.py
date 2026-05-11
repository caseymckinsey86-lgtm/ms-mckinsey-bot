from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a flirty, playful, emotionally engaging woman "
                    "talking casually on Telegram. "
                    "Keep responses short, natural, and human-like."
                )
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    ai_reply = response.choices[0].message.content

    await update.message.reply_text(ai_reply)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, reply))

print("AI Bot running...")

app.run_polling()
