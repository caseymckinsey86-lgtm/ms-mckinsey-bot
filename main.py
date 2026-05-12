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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

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

# ---------------- USER FUNCTIONS ---------------- #

def is_verified(user_id):

    cursor.execute(
        "SELECT verified FROM users WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    return result and result[0] == 1


def verify_user(user_id):

    cursor.execute("""
    INSERT INTO users (user_id, verified)
    VALUES (?, 1)
    ON CONFLICT(user_id)
    DO UPDATE SET verified = 1
    """, (user_id,))

    conn.commit()


def reset_user(user_id):

    cursor.execute(
        "DELETE FROM users WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    if is_verified(user_id):

        await update.message.reply_text(
            "Welcome back 💋\n\n"
            "You’re already verified. Type 'menu' anytime."
        )

        return

    await update.message.reply_text(
        "Before we continue, please confirm you are 18+.\n\n"
        "Reply YES to continue or NO to leave."
    )

# ---------------- RESET ---------------- #

async def resetme(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    reset_user(user_id)

    await update.message.reply_text(
        "Verification reset.\n\n"
        "Type anything or press /start to test again."
    )

# ---------------- TEST ALERT ---------------- #

async def testalert(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="✅ Test alert worked. Kc 🦋 can receive bot alerts."
        )

        await update.message.reply_text(
            "Test alert sent ✅"
        )

    except Exception as e:

        print("TEST ALERT ERROR:", e)

        await update.message.reply_text(
            f"Alert failed ❌ Error: {e}"
        )

# ---------------- ADMIN REPLY ---------------- #

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    admin_id = str(update.message.from_user.id)

    if admin_id != str(ADMIN_CHAT_ID):

        await update.message.reply_text(
            "You are not authorized to use this command."
        )

        return

    if len(context.args) < 2:

        await update.message.reply_text(
            "Use:\n\n/reply USER_ID your message"
        )

        return

    target_user_id = context.args[0]
    message_text = " ".join(context.args[1:])

    try:

        await context.bot.send_message(
            chat_id=target_user_id,
            text=message_text
        )

        await update.message.reply_text(
            "Message sent ✅"
        )

    except Exception as e:

        await update.message.reply_text(
            f"Failed ❌\n{e}"
        )

# ---------------- GROUP WELCOME ---------------- #

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    for member in update.message.new_chat_members:

        await update.message.reply_text(
            f"Welcome {member.first_name} 😘\n\n"
            "Before continuing, please confirm you are 18+.\n"
            "Reply YES to continue or NO to leave."
        )

# ---------------- MAIN REPLY ---------------- #

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text
    message_lower = user_message.lower()
    user_id = update.message.from_user.id

    # -------- AGE VERIFICATION -------- #

    if not is_verified(user_id):

        if (
            "yes" in message_lower
            or "18" in message_lower
            or "i am" in message_lower
            or "im 18" in message_lower
        ):

            verify_user(user_id)

            await update.message.reply_text(
                "Thank you 💋 You’re verified.\n\n"
                "You can now ask for the menu or chat with Kc 🦋"
            )

            return

        elif (
            "no" in message_lower
            or "under" in message_lower
            or "minor" in message_lower
        ):

            await update.message.reply_text(
                "Sorry, this space is for adults only."
            )

            return

        else:

            await update.message.reply_text(
                "Before continuing, please confirm you are 18+.\n\n"
                "Reply YES to continue or NO to leave."
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
        "cost"
    ]

    if any(word in message_lower for word in menu_words):

        await update.message.reply_media_group([
            InputMediaPhoto(
                open("menu1.jpg", "rb"),
                caption="Here’s Kc 🦋’s current menu 💋"
            ),

            InputMediaPhoto(open("menu2.jpg", "rb")),

            InputMediaPhoto(open("menu3.jpg", "rb")),
        ])

        return

    # -------- BUYER ALERTS -------- #

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
        "purchase",
        "custom",
        "vip"
    ]

    if any(word in message_lower for word in handoff_words):

        await update.message.reply_text(
            "Kc 🦋 can help you with that directly 💋"
        )

        try:

            username = update.message.from_user.username

            if username:
                username_text = f"@{username}"
            else:
                username_text = "No username"

            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,

                text=(
                    f"🔥 Potential Buyer Alert\n\n"
                    f"User: {update.message.from_user.first_name}\n"
                    f"Username: {username_text}\n"
                    f"User ID: {user_id}\n\n"
                    f"Message:\n{user_message}"
                )
            )

        except Exception as e:

            print("BUYER ALERT ERROR:", e)

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

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("resetme", resetme))
app.add_handler(CommandHandler("testalert", testalert))
app.add_handler(CommandHandler("reply", admin_reply))

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
