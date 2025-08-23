# Witty Telegram Bot 🤖

A Telegram bot with GPT-3.5-turbo, dark humor personality, and conversation memory.

## Features
- GPT-3.5-turbo responses
- Witty, slightly dark humor personality
- Conversation memory per user
- Broadcast messages to all users (admin only)
- Human-like typing delays

## Setup
1. Clone this repo
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`
4. Fill in your actual API keys
5. `python bot.py`

## Environment Variables
- `TELEGRAM_BOT_TOKEN`: From @BotFather
- `OPENAI_API_KEY`: From platform.openai.com
- `OWNER_ID`: Your Telegram user ID from @userinfobot
