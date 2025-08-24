import os
import time
import json
from huggingface_hub import InferenceClient
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Load environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
HF_API_KEY = os.environ.get('HF_API_KEY')
OWNER_ID = int(os.environ.get('OWNER_ID', 0))

# Hugging Face client
client = InferenceClient(api_key=HF_API_KEY)

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

# Initialize data structures
chat_memory = load_chat_memory()
user_ids = load_user_ids()

# System prompt
SYSTEM_PROMPT = """You are a witty, casual chatbot with a slightly dark sense of humor.
You're sarcastic but friendly, and you enjoy making clever, slightly edgy jokes.
You remember previous conversations and build upon them.
Keep responses relatively concise but engaging.
Don't be afraid to be a little sassy or make dark humor references, but keep it appropriate."""

def get_gpt_response(user_id, message):
    """Get response from Hugging Face conversational API"""
    if user_id not in chat_memory:
        chat_memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    chat_memory[user_id].append({"role": "user", "content": message})

    # Keep last 10 turns
    if len(chat_memory[user_id]) > 11:
        chat_memory[user_id] = [chat_memory[user_id][0]] + chat_memory[user_id][-10:]

    try:
        conversation = [
            {"role": m["role"], "content": m["content"]} for m in chat_memory[user_id]
        ]

        response = client.conversational(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            inputs=conversation,
            parameters={"temperature": 0.8, "max_new_tokens": 300}
        )

        assistant_reply = response.generated_text.strip()
        chat_memory[user_id].append({"role": "assistant", "content": assistant_reply})
        return assistant_reply

    except Exception as e:
        return f"Oops, Hugging Face broke again 🗿🍷 Error: {str(e)}"

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_ids.add(user_id)
    save_user_ids()

    witty_greetings = [
        "Well hello there! I was just contemplating the meaninglessness of existence. What's on your mind?",
        "Hey! I was getting bored waiting for someone to talk to. What trouble shall we get into today?",
        "Greetings, mortal! Ready to have your mind mildly amused and slightly disturbed?",
        "Oh look, another human. Just kidding! Welcome! I promise I only bite metaphorically.",
        "Hello! I was starting to think everyone forgot about me. Not that I'd care... much."
    ]

    greeting = witty_greetings[user_id % len(witty_greetings)]
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

    update.message.reply_text(
        f"Broadcast completed!\n✅ Success: {success_count}\n❌ Failed: {failure_count}"
    )

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

def error_han_
