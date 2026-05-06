import logging
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from .agent import agent
from .config import config

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    username = update.message.from_user.username or "Unknown"
    
    logger.info(f"📩 Telegram incoming: [{username}] ({chat_id}): {user_text}")
    
    # Check if it's a private chat or if the bot is mentioned
    is_private = update.message.chat.type == "private"
    bot_username = context.bot.username
    is_mention = (bot_username in user_text) if bot_username else False
    
    # Also check for GOKU_OWNER_ID if set
    owner_id = os.getenv("GOKU_OWNER_ID")
    if owner_id and chat_id != owner_id and is_private:
        logger.warning(f"🚫 Unauthorized access attempt from {chat_id}")
        await update.message.reply_text("⚠️ Access Denied: You are not my authorized owner.")
        return

    if is_private or is_mention:
        try:
            logger.info(f"🤖 Goku is thinking for {chat_id}...")
            response = await agent.chat(user_text, session_id=f"tg_{chat_id}", source="telegram")
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"❌ Telegram Error: {e}")
            await update.message.reply_text("📦 Sorry, I hit a snag while thinking. Please try again.")

async def start_telegram_bot():
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return

    try:
        application = ApplicationBuilder().token(token).build()
        
        # Add handler for all text messages
        text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        application.add_handler(text_handler)

        logger.info("🐉 Goku Lite: Telegram bot initialized and polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Keep the task alive
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"💥 Failed to start Telegram bot: {e}")
