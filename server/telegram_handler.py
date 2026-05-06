import logging
import asyncio
import os
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from .agent import agent
from .config import config
from .history import history

logger = logging.getLogger(__name__)

def split_message(text, limit=4000):
    """Split a message into chunks within Telegram's character limit."""
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks

async def keep_typing(context, chat_id, stop_event):
    """Pulsing typing indicator."""
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
        except:
            break

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming documents, parse them, and store text in DB."""
    if not update.message or not update.message.document:
        return

    doc = update.message.document
    chat_id = str(update.message.chat_id)
    file_name = doc.file_name
    
    # 1. Safety Check (Max 5MB for RAM safety)
    if doc.file_size > 5 * 1024 * 1024:
        await update.message.reply_text("⚠️ This document is too heavy for my current RAM limit (Max 5MB). Please send a smaller version.")
        return

    # 2. Immediate Feedback
    await update.message.reply_text(f"📥 Received: *{file_name}*. I'm reading it now...", parse_mode="Markdown")
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # 3. Download to a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            new_file = await context.bot.get_file(doc.file_id)
            await new_file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        # 4. Parse Document to Markdown
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(tmp_path)
        content = result.text_content

        # 5. Cleanup local file INSTANTLY
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        # 6. Store Text in Remote DB as a system-level context
        doc_context = f"--- ATTACHED DOCUMENT: {file_name} ---\n{content}\n--- END DOCUMENT ---"
        history.add_message(session_id=f"tg_{chat_id}", role="system", content=doc_context, msg_type="document")
        
        # 7. Notify Agent and Get Response
        await update.message.reply_text("✅ I've finished reading. What would you like to know about this document?")
        
    except Exception as e:
        logger.error(f"❌ Document Processing Error: {e}")
        await update.message.reply_text("📦 Sorry, I had trouble reading that document. Make sure it's a valid PDF, Word, or Excel file.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    username = update.message.from_user.username or "Unknown"
    
    logger.info(f"📩 Telegram incoming: [{username}] ({chat_id}): {user_text}")
    
    is_private = update.message.chat.type == "private"
    bot_username = context.bot.username
    is_mention = (bot_username in user_text) if bot_username else False
    
    owner_id = os.getenv("GOKU_OWNER_ID")
    if owner_id and chat_id != owner_id and is_private:
        logger.warning(f"🚫 Unauthorized access attempt from {chat_id}")
        await update.message.reply_text("⚠️ Access Denied.")
        return

    if is_private or is_mention:
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(context, chat_id, stop_typing))
        
        try:
            await asyncio.sleep(1.2)
            response = await asyncio.wait_for(
                agent.chat(user_text, session_id=f"tg_{chat_id}", source="telegram"),
                timeout=90
            )
            
            await asyncio.sleep(0.5)
            stop_typing.set()
            await typing_task
            
            if response:
                chunks = split_message(response)
                for chunk in chunks:
                    try:
                        await update.message.reply_text(chunk, parse_mode="Markdown")
                    except:
                        await update.message.reply_text(chunk)
                    if len(chunks) > 1: await asyncio.sleep(0.3)
            else:
                await update.message.reply_text("I'm not sure how to respond to that.")
                
        except asyncio.TimeoutError:
            stop_typing.set()
            await update.message.reply_text("⏳ Cloud brain timeout. Please try again.")
        except Exception as e:
            stop_typing.set()
            logger.error(f"❌ Telegram Error: {e}")
            try:
                await update.message.reply_text(f"📦snag: {str(e)[:100]}")
            except: pass
        finally:
            if not stop_typing.is_set(): stop_typing.set()

async def start_telegram_bot():
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set.")
        return

    try:
        application = ApplicationBuilder().token(token).build()
        
        # Text Messages
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        # Documents
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        logger.info("🐉 Goku Lite: Telegram bot initialized with Document Vision...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"💥 Failed to start Telegram bot: {e}")
