import os
import sqlite3

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    verified INTEGER DEFAULT 0
)
""")

conn.commit()

# ---------------- FUNCTIONS ---------------- #

def is_verified(user_id):
    cursor.execute(
        "SELECT verified FROM users WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    return result and result[0] == 1


def verify_user(user_id):
    cursor.execute("""
    INSERT OR REPLACE INTO users (user_id, verified)
    VALUES (?, 1)
    """, (user_id,))

    conn.commit()

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Before we continue, please confirm you are 18+.\n\n"
        "Reply YES to continue or NO to leave."
    )

# ---------------- WELCOME ---------------- #

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    for member in update.message.new_chat_members:

        await update.message.reply_text(
            f"Welcome {member.first_name} 😘\n\n"
            "Before continuing, please confirm you are 18+.\n"
            "Reply YES to continue or NO to leave."
        )

# ---------------- REPLY ---------------- #

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text
    message_lower = user_message.lower()
    user_id = update.message.from_user.id

    # -------- AGE VERIFICATION -------- #

    if not is_verified(user_id):

        if message_lower in [
            "yes",
            "y",
            "18+",
            "yes i am",
            "i am 18"
        ]:

            verify_user(user_id)

            await update.message.reply_text(
                "Thank you 💋 You’re verified.\n\n"
                "You can ask for the menu or just say hey."
            )

            return

        elif message_lower in [
            "no",
            "n",
            "under 18"
        ]:

            await update.message.reply_text(
                "Sorry, this space is for adults only."
            )

            return

        else:

            await update.message.reply_text(
                "Please confirm you are 18+ first.\n\n"
                "Reply YES or NO."
            )

            return

    # -------- MENU -------- #

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
            InputMediaPhoto(
                open("menu1.jpg", "rb"),
                caption="Here’s Kc 🦋’s current menu 💋"
            ),

            InputMediaPhoto(
                open("menu2.jpg", "rb")
            ),

            InputMediaPhoto(
                open("menu3.jpg", "rb")
            ),
        ])

        return

    # -------- HUMAN HANDOFF -------- #

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
            "Kc 🦋 can help you with that directly 💋"
        )

        return

    # -------- AI CHAT -------- #

    try:

        completion = client.chat.completions.create(
            model="gpt-4o-mini",

            messages=[
                {
                    "role": "system",

                    "content": (
                        "You are Kc 🦋’s Telegram assistant. "
                        "Reply short, warm, playful, feminine, "
                        "natural, and human-like. "
                        "No video chat. "
                        "No payments. "
                        "Send serious buyers to Kc 🦋."
                    )
                },

                {
                    "role": "user",
                    "content": user_message
                }
            ],

            max_tokens=50
        )

        ai_reply = completion.choices[0].message.content

        await update.message.reply_text(ai_reply)

    except Exception as e:

        print(e)

        await update.message.reply_text(
            "Oops 😅 my chat brain glitched for a second. Try me again."
        )

# ---------------- APP ---------------- #

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        welcome
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        reply
    )
)

print("AI bot running...")

app.run_polling()
