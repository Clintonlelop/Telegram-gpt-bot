import os
import time
import json
import requests
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Load environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.environ.get('OPENAI_API_KEY')  # Still use OPENAI_API_KEY name for compatibility
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

# Initialize data structures
chat_memory = load_chat_memory()
user_ids = load_user_ids()

# System prompt for the bot's personality
SYSTEM_PROMPT = """You are a witty, casual chatbot with a slightly dark sense of humor. 
You're sarcastic but friendly, and you enjoy making clever, slightly edgy jokes. 
You remember previous conversations and build upon them. 
Keep responses relatively concise but engaging. 
Don't be afraid to be a little sassy or make dark humor references, but keep it appropriate."""

def get_gpt_response(user_id, message):
    """Get response from Groq API (free alternative to OpenAI)"""
    # Get or create user's chat history
    if user_id not in chat_memory:
        chat_memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add user message to history
    chat_memory[user_id].append({"role": "user", "content": message})
    
    # Keep only last 10 messages to manage context length
    if len(chat_memory[user_id]) > 11:  # system + 10 messages
        chat_memory[user_id] = [chat_memory[user_id][0]] + chat_memory[user_id][-10:]
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": chat_memory[user_id],
            "model": "llama-3.1-70b-versatile",  # Free Groq model
            "temperature": 0.8,
            "max_tokens": 500,
            "stream": False
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        assistant_reply = response.json()["choices"][0]["message"]["content"].strip()
        
        # Add assistant response to history
        chat_memory[user_id].append({"role": "assistant", "content": assistant_reply})
        
        return assistant_reply
        
    except Exception as e:
        return f"Oops, my circuits are fried. Error: {str(e)}. Maybe try again when I'm less... broken?"

def start(update: Update, context: CallbackContext):
    """Send a witty greeting when the command /start is issued."""
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
    """Broadcast a message to all users (owner only)"""
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
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
            failure_count += 1
    
    update.message.reply_text(
        f"Broadcast completed!\n"
        f"✅ Success: {success_count}\n"
        f"❌ Failed: {failure_count}"
    )

def handle_message(update: Update, context: CallbackContext):
    """Handle incoming messages and generate responses"""
    user_id = update.effective_user.id
    message = update.message.text
    
    # Add user to tracking
    user_ids.add(user_id)
    save_user_ids()
    
    # Show typing action
    update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Simulate human typing delay (1-2 seconds)
    time.sleep(1 + (user_id % 2))  # Varies per user for more natural feel
    
    # Get Groq response
    response = get_gpt_response(user_id, message)
    
    # Save updated chat memory
    save_chat_memory()
    
    # Send response
    update.message.reply_text(response)

def error_handler(update: Update, context: CallbackContext):
    """Handle errors gracefully"""
    print(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        update.effective_message.reply_text(
            "Well this is awkward... I seem to have malfunctioned. "
            "Maybe try again before I start contemplating my own existence too deeply."
        )

def main():
    """Start the bot"""
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    
    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    
    # Register command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    
    # Register message handler
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Register error handler
    dp.add_error_handler(error_handler)
    
    # Start the Bot
    print("Bot is starting with Groq API...")
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()
    
    # Save data before exiting
    save_chat_memory()
    save_user_ids()

if __name__ == '__main__':
    main()
