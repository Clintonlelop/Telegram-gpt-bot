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
    'text_generation': 'https://api-inference.huggingface.co/models/gpt2',
    'text_classification': 'https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english',
    'summarization': 'https://api-inference.huggingface.co/models/facebook/bart-large-cnn',
    'translation': 'https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-en-fr',
    'sentiment_analysis': 'https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest'
}

class HuggingFaceBot:
    def __init__(self):
        self.current_api = 'text_generation'
        self.headers = {
            'Authorization': f'Bearer {HUGGINGFACE_TOKEN}'
        }
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message and show available commands"""
        welcome_text = """
🤖 *Welcome to Hugging Face Bot!*

I can help you interact with various Hugging Face AI models.

*Available Commands:*
/start - Show this welcome message
/help - Show help information
/models - Show available AI models
/current - Show current active model
/search - Search for models (coming soon)
/switch - Switch between different AI models

Just send me text and I'll process it with the current active model!
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = """
📖 *Help Guide*

*Available Models:*
• Text Generation (GPT-2)
• Text Classification
• Summarization
• Translation (EN→FR)
• Sentiment Analysis

*How to use:*
1. Use /models to see available models
2. Use /switch to change models
3. Use /current to check current model
4. Send text to process with current model

*Example:* Send "Hello, how are you?" for text generation
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def show_models(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available models with inline keyboard"""
        keyboard = [
            [InlineKeyboardButton("📝 Text Generation", callback_data='text_generation')],
            [InlineKeyboardButton("🏷️ Text Classification", callback_data='text_classification')],
            [InlineKeyboardButton("📋 Summarization", callback_data='summarization')],
            [InlineKeyboardButton("🌐 Translation", callback_data='translation')],
            [InlineKeyboardButton("😊 Sentiment Analysis", callback_data='sentiment_analysis')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            '🤖 *Available Models:*\n\nChoose a model to switch to:',
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def switch_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch model command"""
        await self.show_models(update, context)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        model_key = query.data
        if model_key in HUGGINGFACE_APIS:
            self.current_api = model_key
            model_name = model_key.replace('_', ' ').title()
            await query.edit_message_text(
                f"✅ Switched to *{model_name}* model!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Invalid model selection!")
    
    async def show_current_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show currently active model"""
        model_name = self.current_api.replace('_', ' ').title()
        await update.message.reply_text(
            f"🔧 *Current Active Model:*\n{model_name}",
            parse_mode='Markdown'
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages and process with Hugging Face API"""
        user_text = update.message.text
        
        if not user_text.strip():
            await update.message.reply_text("Please send some text to process!")
            return
        
        # Show typing action
        await update.message.chat.send_action(action="typing")
        
        try:
            # Call Hugging Face API
            response = self.call_huggingface_api(user_text)
            
            if response:
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("❌ Sorry, I couldn't process your request. The API might be loading or unavailable.")
        
        except Exception as e:
            logger.error(f"Error calling Hugging Face API: {e}")
            await update.message.reply_text("❌ Sorry, there was an error processing your request. Please try again later.")
    
    def call_huggingface_api(self, text: str) -> str:
        """Call the appropriate Hugging Face API based on current selection"""
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
                return "⚠️ Model is currently loading. Please try again in a few seconds."
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            return "⏰ Request timed out. Please try again."
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None
    
    def format_response(self, api_response) -> str:
        """Format the API response based on the model type"""
        if self.current_api == 'text_generation':
            return api_response[0]['generated_text']
        elif self.current_api == 'text_classification':
            label = api_response[0]['label']
            score = api_response[0]['score']
            return f"Label: {label}\nConfidence: {score:.2%}"
        elif self.current_api == 'summarization':
            return api_response[0]['summary_text']
        elif self.current_api == 'translation':
            return api_response[0]['translation_text']
        elif self.current_api == 'sentiment_analysis':
            best = max(api_response[0], key=lambda x: x['score'])
            return f"Sentiment: {best['label']}\nConfidence: {best['score']:.2%}"
        else:
            return str(api_response)

def main():
    """Start the bot"""
    if not TELEGRAM_TOKEN or not HUGGINGFACE_TOKEN:
        logger.error("Please set TELEGRAM_BOT_TOKEN and HUGGINGFACE_API_TOKEN environment variables")
        return
    
    # Create bot instance
    bot = HuggingFaceBot()
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("models", bot.show_models))
    application.add_handler(CommandHandler("switch", bot.switch_model))
    application.add_handler(CommandHandler("current", bot.show_current_model))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Start the Bot
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
