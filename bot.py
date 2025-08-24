import os
import time
import json
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from huggingface_hub import InferenceClient

# Load environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')  # Hugging Face token
OWNER_ID = int(os.environ.get('OWNER_ID', 0))

# File paths
CHAT_MEMORY_FILE = 'chat_memory.json'
USER_IDS_FILE = 'user_ids.json'

# Initialize Hugging Face client
client = InferenceClient(HF_TOKEN)

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

# Bot personality system prompt
SYSTEM_PROMPT = """You are a witty, casual chatbot with a slightly dark sense of humor. 
You're sarcastic but friendly, and you enjoy making clever, slightly edgy jokes. 
You remember previous conversations and build upon them. 
Keep responses concise, engaging, and slightly sassy."""

# Hugging Face response function
def get_hf_response(user_id, message):
    if user_id not in chat_memory:
        chat_memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    chat_memory[user_id].append({"role": "user", "content": message})

    if len(chat_memory[user_id]) > 11:
        chat_memory[user_id] = [chat_memory[user_id][0]] + chat_memory[user_id][-10:]

    prompt = "\n".join([m['content'] for m in chat_memory[user_id]])
    try:
        output = client.text_generation(
            model="mosaicml/mpt-7b-instruct",
            inputs=prompt,
            max_new_tokens=200,
            temperature=0.8
        )
        assistant_reply = output[0]['generated_text'].strip()
        chat_memory[user_id].append({"role": "assistant", "content": assistant_reply})
        return assistant_reply
    except Exception as e:
        return f"Oops, Hugging Face error: {str(e)}"

# /start command
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

# /broadcast command (owner only)
def broadcast(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        update.message.reply_text("Nice try, but you're not the boss of me. ✋")
        return
    if not context.args:
        update.message.reply_text("Usage: /broadcast Your message here")
        return
    message = " ".join(context.args)
    success, fail = 0, 0
    for uid in user_ids:
        try:
            context.bot.send_message(chat_id=uid, text=f"📢 Broadcast from admin:\n\n{message}")
            success += 1
            time.sleep(0.1)
        except:
            fail += 1
    update.message.reply_text(f"Broadcast completed!\n✅ Success: {success}\n❌ Failed: {fail}")

# Handle incoming messages
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message.text
    user_ids.add(user_id)
    save_user_ids()
    update.message.chat.send_action(action=ChatAction.TYPING)
    time.sleep(1 + (user_id % 2))
    response = get_hf_response(user_id, message)
    save_chat_memory()
    update.message.reply_text(response)

# Error handler
def error_handler(update: Update, context: CallbackContext):
    print(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        update.effective_message.reply_text("Oops, bot malfunctioned. Try again later.")

# Main function
def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_error_handler(error_handler)
    print("Bot is starting on Heroku with Hugging Face...")
    updater.start_polling()
    updater.idle()
    save_chat_memory()
    save_user_ids()

if __name__ == '__main__':
    main()
