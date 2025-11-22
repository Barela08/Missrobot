# bot.py
# Miss — human-like Marathi Duniya Telegram bot (python-telegram-bot v20)
# Fully fixed for PTB v20.3 — Ready for Render

import os, json, random, logging
from datetime import datetime, timezone
from typing import Dict, Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# --------------------
# Config / Persistence
# --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")  
MONGO_URI = os.getenv("MONGO_URI", "")
USE_MONGO = os.getenv("USE_MONGO", "0") == "1"
LOG_CHAT_ID = os.getenv("LOG_CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN environment variable before running.")

ADMIN_IDS = set(int(x) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit())

DATA_FILE = "bot_data.json"

DEFAULT_PERSONA = {
    "name": "Miss",
    "language": "hi",
    "tone": "friendly",
    "signature": "🌸 Miss"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("miss-bot")

def load_data() -> Dict[str, Any]:
    if os.path.isfile(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            log.exception("failed to load data")
    return {"groups": {}}

def save_data(d: Dict[str, Any]):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    except Exception:
        log.exception("failed to save data")

DATA = load_data()

def get_group_conf(chat_id: int):
    key = str(chat_id)
    if key not in DATA["groups"]:
        DATA["groups"][key] = {"autoreply": False, "persona": DEFAULT_PERSONA.copy()}
        save_data(DATA)
    return DATA["groups"][key]

def is_admin_user(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --------------------
# Persona reply logic
# --------------------
GREETINGS = ["हाय", "हैलो", "नमस्ते", "Hi"]
ACTIONS = ["🙂", "😊", "🌸", "✨"]
QUESTION_RESPONSES = [
    "अच्छा प्रश्न! 😊",
    "हूँ... मुझे सोचने दो, पर शायद हाँ।",
    "यह सही लग रहा है।",
    "मैं भी ऐसा मानती हूँ।",
]
STATEMENT_RESPONSES = [
    "ओह सही कहा तुमने।",
    "हम्म… समझ गया।",
    "बहुत अच्छा!",
    "सुनने के लिए धन्यवाद 😊",
]
FALLBACKS = [
    "अच्छा बताओ और?",
    "सच में? थोड़ा और बताओ।",
    "मुझे और बताओ ताकि मैं बेहतर help कर सकूँ।"
]

def make_reply(text: str, persona: Dict[str,Any]) -> str:
    t = (text or "").strip()
    if not t:
        return f"माफ़ करना, मैं समझ नहीं पाई। {random.choice(ACTIONS)}"

    q_words = ["क्यों", "कैसे", "कब", "क्या", "कौन", "कहाँ", "?"]
    if any(q in t for q in q_words):
        return f"{random.choice(QUESTION_RESPONSES)} {random.choice(ACTIONS)} — {persona['name']}"

    if "!" in t or any(ch in t for ch in "😢😠😂❤️"):
        return f"{random.choice(STATEMENT_RESPONSES)} {random.choice(ACTIONS)} — {persona['name']}"

    if len(t.split()) <= 3:
        return f"{random.choice(STATEMENT_RESPONSES)} {random.choice(ACTIONS)} — {persona['name']}"

    sample = " ".join(t.split()[:8])
    return (
        f"तुमने कहा: \"{sample}...\" — {random.choice(FALLBACKS)} "
        f"{random.choice(ACTIONS)}\n— {persona['name']}"
    )

# --------------------
# Command handlers
# --------------------
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "मैं *Miss* — Marathi Duniya assistant.\n\n"
        "Admins commands:\n"
        "/autoreply on|off — enable/disable auto replies in this group\n"
        "/setpersona <name> — change persona name\n"
        "/status — show settings\n"
        "/help — this message\n\n"
        "Triggers: mention the bot or reply to bot."
    )
    await update.effective_chat.send_message(txt, parse_mode=ParseMode.MARKDOWN)

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    conf = get_group_conf(chat.id)
    persona = conf.get("persona", DEFAULT_PERSONA)
    txt = (
        f"Group id: `{chat.id}`\n"
        f"Auto-reply: *{conf.get('autoreply')}*\n"
        f"Persona: *{persona.get('name')}*\n"
    )
    await update.effective_chat.send_message(txt, parse_mode=ParseMode.MARKDOWN)

async def autoreply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.effective_message.reply_text("❌ सिर्फ admins ही यह कर सकते हैं।")
        return

    args = context.args or []
    if not args:
        await update.effective_message.reply_text("Usage: /autoreply on|off")
        return

    v = args[0].lower()
    conf = get_group_conf(update.effective_chat.id)
    conf["autoreply"] = v in ("on", "1", "true", "enable")
    save_data(DATA)

    await update.effective_message.reply_text(
        f"Auto-reply set to {conf['autoreply']}."
    )

async def setpersona_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.effective_message.reply_text("❌ सिर्फ admins ही यह कर सकते हैं।")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /setpersona <name>")
        return

    name = " ".join(context.args).strip()
    conf = get_group_conf(update.effective_chat.id)
    conf["persona"]["name"] = name
    save_data(DATA)

    await update.effective_message.reply_text(
        f"Persona updated to *{name}*",
        parse_mode=ParseMode.MARKDOWN
    )

# --------------------
# Message Handler
# --------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not update.effective_user:
        return

    user = update.effective_user
    if user.is_bot:
        return

    text = msg.text or msg.caption or ""
    conf = get_group_conf(update.effective_chat.id)
    persona = conf["persona"]
    autoreply = conf["autoreply"]

    # Trigger conditions
    replied_to_bot = msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id
    mentioned = context.bot.username.lower() in text.lower() if context.bot.username else False

    if not (autoreply or replied_to_bot or mentioned):
        return

    # cooldown per-user: 6 sec
    key = f"last_reply_{user.id}"
    last_ts = context.chat_data.get(key, 0)
    now_ts = datetime.now(timezone.utc).timestamp()

    if now_ts - last_ts < 6:
        return

    context.chat_data[key] = now_ts
    reply = make_reply(text, persona)

    await msg.reply_text(reply)

# --------------------
# Main
# --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("autoreply", autoreply_handler))
    app.add_handler(CommandHandler("setpersona", setpersona_handler))

    # FIXED: PTB v20 ke sahi filters
    app.add_handler(MessageHandler(filters.TEXT | filters.Caption, message_handler))

    log.info("Miss bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
