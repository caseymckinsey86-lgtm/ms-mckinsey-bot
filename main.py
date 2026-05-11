import os
import asyncio
import random

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    try:

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Ms_McKinsey’s Telegram assistant. "
                        "Be playful, warm, flirty, short, natural, and human-like. "
                        "Never sound robotic or repetitive."
                    )
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=80
        )

        ai_reply = completion.choices[0].message.content

        # Simulated human typing delay
        await asyncio.sleep(random.randint(6, 14))

        await update.message.reply_text(ai_reply)

    except Exception as e:

        print(e)

        await update.message.reply_text(
            "Oops 😅 my chat brain glitched for a second. Try me again."
        )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        reply
    )
)

print("AI bot running...")

app.run_polling()
