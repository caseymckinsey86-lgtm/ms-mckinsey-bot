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
    cursor.execute(
        "SELECT verified FROM users WHERE user_id = ?",
        (user_id,)
    )

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
    cursor.execute(
        "DELETE FROM users WHERE user_id = ?",
        (user_id,)
    )

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
    cursor.execute(
        "SELECT takeover FROM users WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    return result and result[0] == 1

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    if is_verified(user_id):

        await update.message.reply_text(
            "What's on your mind hun? 😘\n\n"
            "Or I can help you with:\n"
            "• Menu\n"
            "• Special Bundles\n"
            "• Premium Chat Service with Kc 🦋\n"
            "• Content Previews\n"
            "• VIP Access"
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

        await query.message.reply_text(
            "Not authorized."
        )

        return

    data = query.data

    # TAKEOVER

    if data.startswith("takeover:"):

        target_user_id = int(data.split(":")[1])

        set_takeover(target_user_id, 1)

        await query.message.reply_text(
            f"💬 Takeover enabled for {target_user_id}"
        )

    # RELEASE

    elif data.startswith("release:"):

        target_user_id = int(data.split(":")[1])

        set_takeover(target_user_id, 0)

        await query.message.reply_text(
            f"✅ AI restored for {target_user_id}"
        )

    # REPLY MODE

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

    if sender_id == str(ADMIN_CHAT_ID):

        if sender_id in admin_reply_targets:

            target_user_id = admin_reply_targets.pop(sender_id)

            try:

                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=user_message
                )

                await update.message.reply_text(
                    "Reply sent ✅"
                )

            except Exception as e:

                await update.message.reply_text(
                    f"Reply failed ❌\n\n{e}"
                )

            return

    # -------- TAKEOVER MODE -------- #

    if is_takeover(user_id):

        try:

            username = update.message.from_user.username

            if username:
                username_text = f"@{username}"
            else:
                username_text = "No username"

            keyboard = InlineKeyboardMarkup([
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
                "What's on your mind hun? 😘\n\n"
                "Or I can help you with:\n\n"
                "• Menu\n"
                "• Special Bundles\n"
                "• Premium Chat Service with Kc 🦋\n"
                "• Content Previews\n"
                "• VIP Access"
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
        "get menu",
        "show menu",
        "price",
        "prices",
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

    # -------- KC HANDOFF -------- #

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
        "chat service",

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

            if username:
                username_text = f"@{username}"
            else:
                username_text = "No username"

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
    "You are Kc 🦋’s flirty Telegram assistant, not Kc herself. "
    "Never pretend to be Kc. "
    "Do not say things like 'it's me, Kc' or 'I'm Kc.' "

    "Your job is to greet users, keep the conversation warm, playful, "
    "and slightly flirty, and guide them toward the right option. "

    "Use phrases like: "
    "'Kc 🦋 can help with that directly 💋' "
    "'I can get Kc’s attention for you hun 😘' "
    "'Want the menu or should I let Kc know you're interested?' "

    "Keep replies short, casual, feminine, and natural. "
    "Do not invent details about services, previews, bundles, VIP, or pricing. "

    "If someone asks about Menu, Special Bundles, Premium Chat Service with Kc 🦋, "
    "Content Previews, VIP Access, customs, buying, payment, or availability, "
    "do not answer as Kc. Tell them Kc 🦋 can help directly. "

    "No video chat. No payment discussion. "
    "Never sound like customer support or an AI robot."
)
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
