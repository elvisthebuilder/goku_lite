import logging
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from .agent import agent
from .config import config

logger = logging.getLogger(__name__)

async def keep_typing(context, chat_id, stop_event):
    """Pulsing typing indicator to keep it alive during long AI thinking."""
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4) # Telegram typing lasts ~5 seconds
        except:
            break

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
        # 1. Start continuous typing pulse
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(context, chat_id, stop_typing))
        
        try:
            logger.info(f"🤖 Goku is thinking for {chat_id}...")
            
            # 2. Get Response with a timeout to prevent hanging
            response = await asyncio.wait_for(
                agent.chat(user_text, session_id=f"tg_{chat_id}", source="telegram"),
                timeout=90 # Wait up to 90s for cloud inference
            )
            
            # 3. Stop typing before sending
            stop_typing.set()
            await typing_task
            
            if response:
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                await update.message.reply_text("I heard you, but I couldn't formulate a response. Try again?")
                
        except asyncio.TimeoutError:
            stop_typing.set()
            logger.error(f"⏱️ Cloud timeout for {chat_id}")
            await update.message.reply_text("⏳ The cloud brain is taking too long to respond. Please try again in a moment.")
        except Exception as e:
            stop_typing.set()
            logger.error(f"❌ Telegram Error: {e}")
            try:
                await update.message.reply_text(f"📦 Error: {str(e)[:100]}")
            except: pass
        finally:
            if not stop_typing.is_set():
                stop_typing.set()

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
        
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"💥 Failed to start Telegram bot: {e}")
