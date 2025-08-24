import os
import time
import json
import requests
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Load environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
HF_API_KEY = os.environ.get('HF_API_KEY')   # Hugging Face key
OWNER_ID = int(os.environ.get('OWNER_ID', 0))

# File paths
CHAT_MEMORY_FILE = 'chat_memory.json'
USER_IDS_FILE = 'user_ids.json'

# Load chat memory
def load_chat_memory():
    try:
        with open(CHAT_MEMORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Load user IDs
def load_user_ids():
    try:
        with open(USER_IDS_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

# Save chat memory
def save_chat_memory():
    with open(CHAT_MEMORY_FILE, 'w') as f:
        json.dump(chat_memory, f, indent=2)

# Save user IDs
def save_user_ids():
    with open(USER_IDS_FILE, 'w') as f:
        json.dump(list(user_ids), f)

# Initialize memory
chat_memory = load_chat_memory()
user_ids = load_user_ids()

# Personality
SYSTEM_PROMPT = """You are a witty, casual chatbot with a slightly dark sense of humor. 
You're sarcastic but friendly, and you enjoy making clever, slightly edgy jokes. 
You remember previous conversations and build upon them. 
Keep responses relatively concise but engaging. 
Don't be afraid to be a little sassy or make dark humor references, but keep it appropriate."""

def get_gpt_response(user_id, message):
    """Get response from Hugging Face API"""
    if user_id not in chat_memory:
        chat_memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    chat_memory[user_id].append({"role": "user", "content": message})

    if len(chat_memory[user_id]) > 11:
        chat_memory[user_id] = [chat_memory[user_id][0]] + chat_memory[user_id][-10:]
    
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": message}

        response = requests.post(
            "https://api-inference.huggingface.co/models/facebook/blenderbot-400M-distill",
            headers=headers,
            json=payload,
            timeout=60
        )

        # Debug logs
        print("Status:", response.status_code)
        print("Raw response:", response.text)

        if response.status_code == 503:
            return "Model is waking up 💤, give me a few seconds and try again 🗿🍷"

        response.raise_for_status()
        result = response.json()

        # Hugging Face returns list with dict
        assistant_reply = result[0]["generated_text"]
        chat_memory[user_id].append({"role": "assistant", "content": assistant_reply})

        return assistant_reply
    
    except Exception as e:
        return f"Oops, Hugging Face broke again 🗿🍷 Error: {str(e)}"

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_ids.add(user_id)
    save_user_ids()

    greetings = [
        "Well hello there! I was just contemplating the meaninglessness of existence. What's on your mind?",
        "Hey! I was getting bored waiting for someone to talk to. What trouble shall we get into today?",
        "Greetings, mortal! Ready to have your mind mildly amused and slightly disturbed?",
        "Oh look, another human. Just kidding! Welcome! I promise I only bite metaphorically.",
        "Hello! I was starting to think everyone forgot about me. Not that I'd care... much."
    ]

    greeting = greetings[user_id % len(greetings)]
    update.message.reply_text(greeting)

def broadcast(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        update.message.reply_text("Nice try, but you're not the boss of me. ✋")
        return
    
    if not context.args:
        update.message.reply_text("Usage: /broadcast Your message here")
        return
    
    message = " ".join(context.args)
    success_count = 0
    failure_count = 0
    
    for uid in user_ids:
        try:
            context.bot.send_message(chat_id=uid, text=f"📢 Broadcast from admin:\n\n{message}")
            success_count += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
            failure_count += 1
    
    update.message.reply_text(f"Broadcast done!\n✅ {success_count} users\n❌ {failure_count} failed")

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message.text
    user_ids.add(user_id)
    save_user_ids()

    update.message.chat.send_action(action=ChatAction.TYPING)
    time.sleep(1 + (user_id % 2))

    response = get_gpt_response(user_id, message)
    save_chat_memory()
    update.message.reply_text(response)

def error_handler(update: Update, context: CallbackContext):
    print(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        update.effective_message.reply_text("Well this is awkward... my brain glitched out 🤯")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_error_handler(error_handler)

    print("Bot is starting with Hugging Face API...")
    updater.start_polling()
    updater.idle()
    save_chat_memory()
    save_user_ids()

if __name__ == '__main__':
    main()
