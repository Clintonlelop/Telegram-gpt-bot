import os
import time
import json
import requests
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
HF_API_KEY = os.environ.get("HF_API_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))

# File storage
CHAT_MEMORY_FILE = "chat_memory.json"
USER_IDS_FILE = "user_ids.json"

def load_json(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

chat_memory = load_json(CHAT_MEMORY_FILE, {})
user_ids = set(load_json(USER_IDS_FILE, []))

SYSTEM_PROMPT = """You are a witty, casual chatbot with a slightly dark sense of humor.
You're sarcastic but friendly, you enjoy clever edgy jokes, but keep it appropriate."""

def get_gpt_response(user_id, message):
    if user_id not in chat_memory:
        chat_memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    chat_memory[user_id].append({"role": "user", "content": message})

    if len(chat_memory[user_id]) > 11:
        chat_memory[user_id] = [chat_memory[user_id][0]] + chat_memory[user_id][-10:]

    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {
            "inputs": chat_memory[user_id],
            "parameters": {"max_new_tokens": 300, "temperature": 0.8}
        }

        response = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
            headers=headers,
            json=payload,
            timeout=60
        )

        data = response.json()
        if "error" in data:
            return f"Oops, Hugging Face broke again 🗿🍷 Error: {data['error']}"

        assistant_reply = data[0]["generated_text"].strip()
        chat_memory[user_id].append({"role": "assistant", "content": assistant_reply})
        return assistant_reply

    except Exception as e:
        return f"Error: {str(e)}"

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_ids.add(user_id)
    save_json(USER_IDS_FILE, list(user_ids))
    greetings = [
        "Yo, another human joins the chaos. What's up?",
        "Ah, company at last. Tell me something funny.",
        "Greetings mortal, I promise to only roast you a little 🗿🍷"
    ]
    update.message.reply_text(greetings[user_id % len(greetings)])

def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("Not today, boss wannabe. ✋")
        return
    if not context.args:
        update.message.reply_text("Usage: /broadcast Your message here")
        return
    message = " ".join(context.args)
    for uid in user_ids:
        try:
            context.bot.send_message(chat_id=uid, text=f"📢 Broadcast:\n{message}")
            time.sleep(0.1)
        except:
            pass

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    msg = update.message.text
    user_ids.add(user_id)
    save_json(USER_IDS_FILE, list(user_ids))
    update.message.chat.send_action(action=ChatAction.TYPING)
    time.sleep(1)
    reply = get_gpt_response(user_id, msg)
    save_json(CHAT_MEMORY_FILE, chat_memory)
    update.message.reply_text(reply)

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    print("Bot is alive 🚀")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
