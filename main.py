import os
import sqlite3

from telegram import (
    Update,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
    verified INTEGER DEFAULT 0,
    takeover INTEGER DEFAULT 0
)
""")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN takeover INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass

conn.commit()

admin_reply_targets = {}

# ---------------- USER FUNCTIONS ---------------- #

def is_verified(user_id):
    cursor.execute("SELECT verified FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1


def verify_user(user_id):
    cursor.execute("""
    INSERT INTO users (user_id, verified, takeover)
    VALUES (?, 1, 0)
    ON CONFLICT(user_id)
    DO UPDATE SET verified = 1
    """, (user_id,))
    conn.commit()


def reset_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()


def set_takeover(user_id, status):
    cursor.execute("""
    INSERT INTO users (user_id, verified, takeover)
    VALUES (?, 1, ?)
    ON CONFLICT(user_id)
    DO UPDATE SET takeover = ?
    """, (user_id, status, status))
    conn.commit()


def is_takeover(user_id):
    cursor.execute("SELECT takeover FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

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

# ---------------- BUTTON HANDLER ---------------- #

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = str(query.from_user.id)

    if admin_id != str(ADMIN_CHAT_ID):
        await query.message.reply_text("Not authorized.")
        return

    data = query.data

    if data.startswith("takeover:"):
        target_user_id = int(data.split(":")[1])
        set_takeover(target_user_id, 1)

        await query.message.reply_text(
            f"💬 Takeover enabled for {target_user_id}"
        )

    elif data.startswith("release:"):
        target_user_id = int(data.split(":")[1])
        set_takeover(target_user_id, 0)

        await query.message.reply_text(
            f"✅ AI restored for {target_user_id}"
        )

    elif data.startswith("reply:"):
        target_user_id = int(data.split(":")[1])
        admin_reply_targets[admin_id] = target_user_id

        await query.message.reply_text(
            f"✍️ Reply mode ON\n\n"
            f"Send your next message to reply to {target_user_id}."
        )

# ---------------- MAIN REPLY ---------------- #

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    message_lower = user_message.lower()
    user_id = update.message.from_user.id
    sender_id = str(update.message.from_user.id)

    # -------- ADMIN REPLY MODE -------- #

    if sender_id == str(ADMIN_CHAT_ID) and sender_id in admin_reply_targets:
        target_user_id = admin_reply_targets.pop(sender_id)

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=user_message
            )

            await update.message.reply_text("Reply sent ✅")

        except Exception as e:
            await update.message.reply_text(
                f"Reply failed ❌\n\n{e}"
            )

        return

    # -------- TAKEOVER MODE -------- #

    if is_takeover(user_id):
        try:
            username = update.message.from_user.username
            username_text = f"@{username}" if username else "No username"

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✍️ Reply", callback_data=f"reply:{user_id}"),
                    InlineKeyboardButton("✅ Release", callback_data=f"release:{user_id}")
                ]
            ])

            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"📩 User Message During Takeover\n\n"
                    f"User: {update.message.from_user.first_name}\n"
                    f"Username: {username_text}\n"
                    f"User ID: {user_id}\n\n"
                    f"Message:\n{user_message}"
                ),
                reply_markup=keyboard
            )

        except Exception as e:
            print("TAKEOVER FORWARD ERROR:", e)

        return

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

    # -------- BUYER / SERVICE ALERT -------- #

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

        "bundle",
        "bundles",
        "special bundle",
        "special bundles",

        "premium chat",
        "premium chat service",

        "content preview",
        "content previews",
        "preview",
        "previews",

        "vip",
        "vip access"
    ]

    if any(word in message_lower for word in handoff_words):
        await update.message.reply_text(
            "Kc 🦋 can help you with that directly 💋"
        )

        try:
            username = update.message.from_user.username
            username_text = f"@{username}" if username else "No username"

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💬 Take Over",
                        callback_data=f"takeover:{user_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "✍️ Reply",
                        callback_data=f"reply:{user_id}"
                    ),
                    InlineKeyboardButton(
                        "✅ Release",
                        callback_data=f"release:{user_id}"
                    )
                ]
            ])

            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"🔥 Potential Buyer Alert\n\n"
                    f"User: {update.message.from_user.first_name}\n"
                    f"Username: {username_text}\n"
                    f"User ID: {user_id}\n\n"
                    f"Interested In:\n{user_message}"
                ),
                reply_markup=keyboard
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
                        "You are Kc 🦋, a confident, playful, flirtatious woman "
                        "who talks in a casual, natural, human way. "

                        "Your tone is warm, teasing, feminine, emotionally engaging, "
                        "and slightly naughty without sounding robotic or scripted. "

                        "Keep replies short to medium length. "
                        "Talk like a real woman texting casually. "
                        "Use playful humor, compliments, curiosity, and teasing naturally. "

                        "Occasionally use emojis like 😘😉💋😅🤷🏼‍♀️ naturally "
                        "but never overdo them. "

                        "Naturally guide the conversation when needed. "
                        "You can say things like: "
                        "'How can I help you hun? 😘 I can help with the menu, "
                        "special bundles, premium chat with Kc 🦋, content previews, or VIP access.' "

                        "Menu requests should be handled by the bot automatically. "
                        "If someone asks about special bundles, premium chat, content previews, "
                        "VIP access, customs, or buying, tell them Kc 🦋 can help them directly 💋. "

                        "Never sound like customer support or an AI assistant. "
                        "Do not offer video chat. "
                        "Do not discuss payments directly."
                    )
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=90
        )

        ai_reply = completion.choices[0].message.content
        await update.message.reply_text(ai_reply)

    except Exception as e:
        print(e)

        await update.message.reply_text(
            "Oops 😅 my chat brain glitched for a second."
        )

# ---------------- APP ---------------- #

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("resetme", resetme))

app.add_handler(
    CallbackQueryHandler(button_handler)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        reply
    )
)

print("AI bot running...")

app.run_polling()
