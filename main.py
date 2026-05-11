import os

from telegram import Update, InputMediaPhoto
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
    message_lower = user_message.lower()

    # MENU REQUESTS
    menu_words = [
        "menu",
        "services",
        "offers",
        "options",
        "prices",
        "price",
        "cost",
        "vip"
    ]

    if any(word in message_lower for word in menu_words):

        await update.message.reply_media_group([
            InputMediaPhoto(open("menu1.jpg", "rb"), caption="Here’s Kc 🦋’s current menu 💋"),
            InputMediaPhoto(open("menu2.jpg", "rb")),
            InputMediaPhoto(open("menu3.jpg", "rb")),
        ])

        return

    # HUMAN HANDOFF
    handoff_words = [
        "buy",
        "payment",
        "pay",
        "cashapp",
        "paypal",
        "venmo",
        "refund",
        "available",
        "order",
        "purchase"
    ]

    if any(word in message_lower for word in handoff_words):

        await update.message.reply_text(
            "Kc 🦋 can help you with that directly. 💋"
        )

        return

    try:

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Kc 🦋’s Telegram assistant. "
                        "Speak in a playful, warm, feminine, flirty, human-like way. "
                        "Keep responses short and natural. "
                        "You may recommend VIP access, private content, custom requests, "
                        "priority chat, and bundle deals when relevant. "
                        "Do not offer video chat. "
                        "Do not negotiate prices or accept payments. "
                        "If users ask about payments, purchases, or availability, "
                        "tell them Kc 🦋 can help them directly."
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
