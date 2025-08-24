import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')

# Hugging Face API endpoints
HUGGINGFACE_APIS = {
    'casual_chat': 'https://api-inference.huggingface.co/models/microsoft/DialoGPT-large',
    'text_generation': 'https://api-inference.huggingface.co/models/gpt2',
    'text_classification': 'https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english',
    'summarization': 'https://api-inference.huggingface.co/models/facebook/bart-large-cnn',
    'translation': 'https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-en-fr',
    'sentiment_analysis': 'https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest'
}

class AIChatBot:
    def __init__(self):
        self.current_api = 'casual_chat'  # Default to chat mode
        self.headers = {
            'Authorization': f'Bearer {HUGGINGFACE_TOKEN}'
        }
        # Store conversation history for each user
        self.conversations = {}
        
    def get_conversation_history(self, user_id):
        """Get or create conversation history for a user"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        return self.conversations[user_id]
    
    def add_to_conversation(self, user_id, message, is_bot=False):
        """Add message to conversation history"""
        history = self.get_conversation_history(user_id)
        role = "assistant" if is_bot else "user"
        history.append({"role": role, "content": message})
        
        # Keep only last 10 messages to avoid context overflow
        if len(history) > 10:
            self.conversations[user_id] = history[-10:]
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        user_id = update.effective_user.id
        self.get_conversation_history(user_id)  # Initialize conversation
        
        welcome_text = """
🤖 *Hello! I'm your AI Chat Companion!*

I'm here to chat with you about anything! I can also help with various tasks:

*💬 Casual Chat* - Just talk to me like a friend!
*📝 Text Generation* - Creative writing help
*📋 Summarization* - Summarize long texts
*🌐 Translation* - Translate between languages
*😊 Sentiment Analysis* - Analyze emotions in text

Use /modes to switch between different capabilities, or just start chatting! 😊
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
        # Send a friendly first message
        first_message = "Hey there! 👋 How's your day going? What would you like to chat about? 😄"
        self.add_to_conversation(user_id, first_message, is_bot=True)
        await update.message.reply_text(first_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = """
📖 *Chat Bot Help Guide*

*How to use me:*
• Just send me messages and I'll respond naturally!
• Use /modes to switch between different capabilities
• Use /current to see my current mode
• Use /clear to reset our conversation
• Use /help to see this message again

*I can:*
• Have casual conversations 💬
• Help with creative writing 📝
• Summarize text 📋
• Translate languages 🌐
• Analyze emotions in text 😊

*Example conversation starters:*
"Hey! How are you doing today?"
"Tell me a fun fact!"
"What do you think about artificial intelligence?"
"Can you help me write a story?"
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def show_modes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available modes with inline keyboard"""
        keyboard = [
            [InlineKeyboardButton("💬 Casual Chat", callback_data='casual_chat')],
            [InlineKeyboardButton("📝 Text Generation", callback_data='text_generation')],
            [InlineKeyboardButton("📋 Summarization", callback_data='summarization')],
            [InlineKeyboardButton("🌐 Translation", callback_data='translation')],
            [InlineKeyboardButton("😊 Sentiment Analysis", callback_data='sentiment_analysis')],
            [InlineKeyboardButton("🏷️ Text Classification", callback_data='text_classification')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            '🤖 *Available Modes:*\n\nChoose how you want me to respond:',
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def switch_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch mode command"""
        await self.show_modes(update, context)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        mode_key = query.data
        if mode_key in HUGGINGFACE_APIS:
            self.current_api = mode_key
            mode_name = self.get_mode_display_name(mode_key)
            await query.edit_message_text(
                f"✅ Switched to *{mode_name}* mode!\n\nHow can I help you? 😊",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Invalid mode selection!")
    
    def get_mode_display_name(self, mode_key):
        """Get friendly display name for mode"""
        names = {
            'casual_chat': '💬 Casual Chat',
            'text_generation': '📝 Text Generation',
            'text_classification': '🏷️ Text Classification',
            'summarization': '📋 Summarization',
            'translation': '🌐 Translation',
            'sentiment_analysis': '😊 Sentiment Analysis'
        }
        return names.get(mode_key, mode_key.replace('_', ' ').title())
    
    async def show_current_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show currently active mode"""
        mode_name = self.get_mode_display_name(self.current_api)
        await update.message.reply_text(
            f"🔧 *Current Mode:*\n{mode_name}\n\nWhat would you like to do? 😊",
            parse_mode='Markdown'
        )
    
    async def clear_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear conversation history"""
        user_id = update.effective_user.id
        if user_id in self.conversations:
            self.conversations[user_id] = []
        await update.message.reply_text(
            "🧹 Conversation cleared! Let's start fresh! What would you like to talk about? 😊"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages and generate responses"""
        user_text = update.message.text
        user_id = update.effective_user.id
        
        if not user_text.strip():
            await update.message.reply_text("Please send me a message to chat! 😊")
            return
        
        # Show typing action
        await update.message.chat.send_action(action="typing")
        
        # Add user message to conversation history
        self.add_to_conversation(user_id, user_text, is_bot=False)
        
        try:
            # Generate response based on current mode
            if self.current_api == 'casual_chat':
                response = self.generate_chat_response(user_id, user_text)
            else:
                response = self.call_huggingface_api(user_text)
            
            if response:
                # Add bot response to conversation history
                self.add_to_conversation(user_id, response, is_bot=True)
                await update.message.reply_text(response)
            else:
                error_msg = "❌ Sorry, I'm having trouble thinking right now. Maybe try again in a moment? 😅"
                await update.message.reply_text(error_msg)
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            error_msg = "❌ Oops! Something went wrong. Let me reset our conversation and try again! 🧹"
            if user_id in self.conversations:
                self.conversations[user_id] = []
            await update.message.reply_text(error_msg)
    
    def generate_chat_response(self, user_id, user_text):
        """Generate conversational response using conversation history"""
        conversation_history = self.get_conversation_history(user_id)
        
        # For casual chat, use the dialog model
        api_url = HUGGINGFACE_APIS['casual_chat']
        
        # Prepare conversation context
        context = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_history[-6:]  # Last 6 messages for context
        ])
        
        payload = {
            "inputs": {
                "text": user_text,
                "past_user_inputs": [msg["content"] for msg in conversation_history if msg["role"] == "user"][-3:],
                "generated_responses": [msg["content"] for msg in conversation_history if msg["role"] == "assistant"][-3:]
            },
            "parameters": {
                "max_length": 150,
                "temperature": 0.9,
                "do_sample": True
            }
        }
        
        try:
            response = requests.post(
                api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'generated_text' in result:
                    return result['generated_text']
                else:
                    return "I'm not sure what to say! Tell me more about that. 😊"
            else:
                logger.warning(f"Chat API returned {response.status_code}")
                return self.get_fallback_response(user_text)
                
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return self.get_fallback_response(user_text)
    
    def get_fallback_response(self, user_text):
        """Fallback responses when API fails"""
        fallbacks = [
            "That's interesting! Tell me more about that. 😊",
            "I'd love to hear more about what you're thinking!",
            "That's a great point! What else is on your mind?",
            "I'm listening! Please continue. 👂",
            "Fascinating! I'd like to know more about that.",
            "You've got my attention! What else would you like to share?",
            "I'm really enjoying our conversation! What's next? 😄"
        ]
        import random
        return random.choice(fallbacks)
    
    def call_huggingface_api(self, text: str) -> str:
        """Call the appropriate Hugging Face API based on current mode"""
        api_url = HUGGINGFACE_APIS[self.current_api]
        
        payload = {"inputs": text}
        
        try:
            response = requests.post(
                api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return self.format_response(response.json())
            elif response.status_code == 503:
                return "⚠️ I'm still waking up! Please try again in a few seconds. 😴"
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            return "⏰ I'm thinking too hard! Let me try that again. 😅"
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None
    
    def format_response(self, api_response) -> str:
        """Format the API response based on the mode"""
        if self.current_api == 'text_generation':
            return api_response[0]['generated_text']
        elif self.current_api == 'text_classification':
            label = api_response[0]['label']
            score = api_response[0]['score']
            return f"I think this text is: {label}\nConfidence: {score:.2%} 🎯"
        elif self.current_api == 'summarization':
            return f"📋 Here's my summary:\n\n{api_response[0]['summary_text']}"
        elif self.current_api == 'translation':
            return f"🌐 Translation:\n{api_response[0]['translation_text']}"
        elif self.current_api == 'sentiment_analysis':
            best = max(api_response[0], key=lambda x: x['score'])
            sentiment_emoji = {
                'positive': '😊',
                'negative': '😔', 
                'neutral': '😐'
            }
            emoji = sentiment_emoji.get(best['label'].lower(), '🤔')
            return f"Emotion: {best['label']} {emoji}\nConfidence: {best['score']:.2%}"
        else:
            return str(api_response)

def main():
    """Start the bot"""
    if not TELEGRAM_TOKEN or not HUGGINGFACE_TOKEN:
        logger.error("Please set TELEGRAM_BOT_TOKEN and HUGGINGFACE_API_TOKEN environment variables")
        return
    
    # Create bot instance
    bot = AIChatBot()
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("modes", bot.show_modes))
    application.add_handler(CommandHandler("switch", bot.switch_mode))
    application.add_handler(CommandHandler("current", bot.show_current_mode))
    application.add_handler(CommandHandler("clear", bot.clear_chat))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Start the Bot
    logger.info("AI Chat Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
