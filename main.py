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

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    name TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0
)
""")

conn.commit()

admin_reply_targets = {}

# ---------------- STATS FUNCTIONS ---------------- #

def inc_stat(name):
    cursor.execute("""
    INSERT INTO stats (name, count)
    VALUES (?, 1)
    ON CONFLICT(name)
    DO UPDATE SET count = count + 1
    """, (name,))
    conn.commit()


def get_stat(name):
    cursor.execute("SELECT count FROM stats WHERE name = ?", (name,))
    result = cursor.fetchone()
    return result[0] if result else 0

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

# ---------------- COMMANDS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if is_verified(user_id):
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

    await update.message.reply_text(
        "Before we continue, please confirm you are 18+.\n\n"
        "Reply YES to continue or NO to leave."
    )


async def resetme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reset_user(user_id)

    await update.message.reply_text(
        "Verification reset.\n\n"
        "Type anything or press /start to test again."
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = str(update.message.from_user.id)

    if admin_id != str(ADMIN_CHAT_ID):
        await update.message.reply_text("Not authorized.")
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE verified = 1")
    verified_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE takeover = 1")
    active_takeovers = cursor.fetchone()[0]

    await update.message.reply_text(
        "📊 Bot Stats\n\n"
        f"Total Users: {total_users}\n"
        f"Verified Users: {verified_users}\n"
        f"Active Takeovers: {active_takeovers}\n\n"
        f"Menu Requests: {get_stat('menu_requests')}\n"
        f"Lead Alerts: {get_stat('lead_alerts')}\n"
        f"Admin Replies: {get_stat('admin_replies')}\n"
        f"Takeovers: {get_stat('takeovers')}\n"
        f"Releases: {get_stat('releases')}"
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
        inc_stat("takeovers")

        await query.message.reply_text(
            f"💬 Takeover enabled for {target_user_id}"
        )

    elif data.startswith("release:"):
        target_user_id = int(data.split(":")[1])
        set_takeover(target_user_id, 0)
        inc_stat("releases")

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
    user_id = update.message.from_user.id
    sender_id = str(update.message.from_user.id)

    user_message = update.message.text or update.message.caption or ""
    message_lower = user_message.lower()

    # -------- ADMIN REPLY MODE -------- #

    if sender_id == str(ADMIN_CHAT_ID) and sender_id in admin_reply_targets:
        target_user_id = admin_reply_targets.pop(sender_id)

        try:
            if update.message.text:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=update.message.text
                )

            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption
                )

            elif update.message.video:
                await context.bot.send_video(
                    chat_id=target_user_id,
                    video=update.message.video.file_id,
                    caption=update.message.caption
                )

            inc_stat("admin_replies")
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

            if update.message.text:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f"📩 User Message During Takeover\n\n"
                        f"User: {update.message.from_user.first_name}\n"
                        f"Username: {username_text}\n"
                        f"User ID: {user_id}\n\n"
                        f"Message:\n{update.message.text}"
                    ),
                    reply_markup=keyboard
                )

            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=ADMIN_CHAT_ID,
                    photo=update.message.photo[-1].file_id,
                    caption=(
                        f"📸 Photo During Takeover\n\n"
                        f"User: {update.message.from_user.first_name}\n"
                        f"Username: {username_text}\n"
                        f"User ID: {user_id}\n\n"
                        f"Caption: {update.message.caption or 'No caption'}"
                    ),
                    reply_markup=keyboard
                )

            elif update.message.video:
                await context.bot.send_video(
                    chat_id=ADMIN_CHAT_ID,
                    video=update.message.video.file_id,
                    caption=(
                        f"🎥 Video During Takeover\n\n"
                        f"User: {update.message.from_user.first_name}\n"
                        f"Username: {username_text}\n"
                        f"User ID: {user_id}\n\n"
                        f"Caption: {update.message.caption or 'No caption'}"
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
        inc_stat("menu_requests")

        await update.message.reply_media_group([
            InputMediaPhoto(open("menu1.jpg", "rb"), caption="Here’s Kc 🦋’s current menu 💋"),
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
        inc_stat("lead_alerts")

        await update.message.reply_text(
            "Let me see if Kc 🦋 is available to help you with that directly hun 💋"
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
                        "You are Kc 🦋’s flirty Telegram assistant, not Kc herself. "
                        "Never pretend to be Kc. "
                        "Do not say things like 'it's me, Kc' or 'I'm Kc.' "
                        "Your job is to greet users, keep the conversation warm, playful, "
                        "and slightly flirty, and guide them toward the right option. "
                        "Keep replies short, casual, feminine, and natural. "
                        "Do not invent details about services, previews, bundles, VIP, or pricing. "
                        "If someone asks about premium services, buying, payment, or availability, "
                        "tell them Kc 🦋 can help directly. "
                        "No video chat. No payment discussion. "
                        "Never sound like customer support or an AI robot."
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
app.add_handler(CommandHandler("stats", stats))

app.add_handler(CallbackQueryHandler(button_handler))

app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        reply
    )
)

print("AI bot running...")

app.run_polling()
