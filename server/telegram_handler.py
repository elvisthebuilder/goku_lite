import logging
import asyncio
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
    
    logger.info(f"Telegram message from {chat_id}: {user_text}")
    
    # Simple logic: Respond if it's a private chat or if mentioned
    is_private = update.message.chat.type == "private"
    is_mention = context.bot.username in user_text if context.bot.username else False
    
    if is_private or is_mention:
        response = await agent.chat(user_text, session_id=f"tg_{chat_id}", source="telegram")
        
        # Check if ElevenLabs is configured and user wants voice
        if os.getenv("ELEVENLABS_API_KEY") and "[VOICE]" in user_text.upper():
            voice_path = await voice_engine.text_to_speech(response)
            if voice_path:
                with open(voice_path, "rb") as audio:
                    await update.message.reply_voice(audio)
                os.remove(voice_path)
            else:
                await update.message.reply_text(response)
        else:
            await update.message.reply_text(response)

async def start_telegram_bot():
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return

    application = ApplicationBuilder().token(token).build()
    
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(text_handler)

    logger.info("🐉 Goku Lite: Telegram bot starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep it running
    while True:
        await asyncio.sleep(3600)
