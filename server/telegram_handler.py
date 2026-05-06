import logging
import asyncio
import os
import tempfile
from collections import defaultdict
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from .agent import agent
from .config import config
from .history import history

logger = logging.getLogger(__name__)

# Global bot instance for proactive messaging
_bot_instance: Bot = None

# Per-user debounce state
_user_timers: dict = {}
_user_message_buffers: dict = defaultdict(list)
_user_locks: dict = defaultdict(asyncio.Lock)

DEBOUNCE_SECONDS = 2.5  # Wait this long after last message before processing

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle official bot commands."""
    if not update.message:
        return

    command = update.message.text.split()[0].lower()
    chat_id = str(update.message.chat_id)
    session_id = f"tg_{chat_id}"

    # Security check
    owner_id = os.getenv("GOKU_OWNER_ID")
    if owner_id and chat_id != owner_id:
        await update.message.reply_text("⚠️ Unauthorized.")
        return

    if command == "/start":
        await update.message.reply_text("🐉 *Link Established.*\nI am awake and monitoring your systems. Speak when you're ready.", parse_mode="Markdown")
    
    elif command == "/new":
        history.clear_session(session_id)
        await update.message.reply_text("🧼 *Context Cleared.*\nI've wiped our recent history. I'm ready to read myself into being again.", parse_mode="Markdown")
    
    elif command == "/status":
        await update.message.reply_text("🔍 *Health Check Initiated...*", parse_mode="Markdown")
        from .scheduler import _health_check
        await _health_check()
    
    elif command == "/briefing":
        await update.message.reply_text("📊 *Generating Briefing...*", parse_mode="Markdown")
        from .scheduler import _morning_briefing
        await _morning_briefing()
    
    elif command == "/help":
        help_text = (
            "🐉 *Goku Command Center*\n\n"
            "/start - Initialize connection\n"
            "/new - Clear current chat history\n"
            "/status - Live system health check\n"
            "/briefing - Trigger daily report\n"
            "/help - Show this menu"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

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
    """Pulsing typing indicator to keep it alive."""
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
        except:
            break

async def process_user_messages(chat_id: str, context: ContextTypes.DEFAULT_TYPE, reply_to_message):
    """
    Process all buffered messages for a user after the debounce window.
    Combines related messages into a single conversational context.
    """
    async with _user_locks[chat_id]:
        messages = _user_message_buffers.pop(chat_id, [])
        if not messages:
            return

        # Combine all buffered messages into one smart context
        if len(messages) == 1:
            combined_text = messages[0]
        else:
            # Merge messages naturally - let Goku see them as a flowing thought
            combined_text = "\n".join(messages)
            logger.info(f"📦 Batching {len(messages)} messages from {chat_id}: {combined_text[:80]}...")

        # Start typing indicator
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(context, chat_id, stop_typing))

        try:
            await asyncio.sleep(1.0)  # Reading pause
            logger.info(f"🤖 Goku is thinking for {chat_id}...")

            response = await asyncio.wait_for(
                agent.chat(combined_text, session_id=f"tg_{chat_id}", source="telegram"),
                timeout=90
            )

            await asyncio.sleep(0.5)
            stop_typing.set()
            await typing_task

            if response:
                chunks = split_message(response)
                for i, chunk in enumerate(chunks):
                    try:
                        await reply_to_message.reply_text(chunk, parse_mode="Markdown")
                    except Exception:
                        await reply_to_message.reply_text(chunk)
                    if len(chunks) > 1:
                        await asyncio.sleep(0.3)
            else:
                await reply_to_message.reply_text("I'm not sure how to respond to that.")

        except asyncio.TimeoutError:
            stop_typing.set()
            await reply_to_message.reply_text("⏳ The cloud brain is taking too long. Please try again.")
        except Exception as e:
            stop_typing.set()
            logger.error(f"❌ Telegram Error: {e}")
            try:
                await reply_to_message.reply_text(f"📦 Snag: {str(e)[:100]}")
            except:
                pass
        finally:
            if not stop_typing.is_set():
                stop_typing.set()

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

    if not (is_private or is_mention):
        return

    # Immediately show "seen" typing signal
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Buffer this message
    _user_message_buffers[chat_id].append(user_text)

    # Cancel existing debounce timer for this user
    if chat_id in _user_timers and not _user_timers[chat_id].done():
        _user_timers[chat_id].cancel()

    # Start a new debounce timer
    async def debounced_process():
        await asyncio.sleep(DEBOUNCE_SECONDS)
        await process_user_messages(chat_id, context, update.message)

    _user_timers[chat_id] = asyncio.create_task(debounced_process())

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming documents, parse them, and store text in DB."""
    if not update.message or not update.message.document:
        return

    doc = update.message.document
    chat_id = str(update.message.chat_id)
    file_name = doc.file_name

    if doc.file_size > 5 * 1024 * 1024:
        await update.message.reply_text("⚠️ Doc too heavy (Max 5MB). Send a smaller version.")
        return

    await update.message.reply_text(f"📥 Got *{file_name}*. Reading it now...", parse_mode="Markdown")
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp:
            new_file = await context.bot.get_file(doc.file_id)
            await new_file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(tmp_path)
        content = result.text_content

        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        doc_context = f"--- ATTACHED DOCUMENT: {file_name} ---\n{content}\n--- END DOCUMENT ---"
        history.add_message(session_id=f"tg_{chat_id}", role="system", content=doc_context, msg_type="document")

        await update.message.reply_text("✅ Done reading! What would you like to know about this document?")

    except Exception as e:
        logger.error(f"❌ Document Processing Error: {e}")
        await update.message.reply_text("📦 Trouble reading that doc. Make sure it's a valid PDF, Word, or Excel file.")

async def send_proactive_message(chat_id: str, text: str):
    """Send a message to a user without them initiating the conversation."""
    global _bot_instance
    if not _bot_instance:
        logger.error("Bot not initialized. Cannot send proactive message.")
        return False
    try:
        chunks = split_message(text)
        for chunk in chunks:
            try:
                await _bot_instance.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
            except:
                await _bot_instance.send_message(chat_id=chat_id, text=chunk)
            await asyncio.sleep(0.3)
        return True
    except Exception as e:
        logger.error(f"Failed to send proactive message: {e}")
        return False

async def start_telegram_bot():
    global _bot_instance
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set.")
        return

    try:
        application = ApplicationBuilder().token(token).build()
        _bot_instance = application.bot

        # Add Command Handlers
        application.add_handler(CommandHandler(["start", "new", "status", "briefing", "help"], handle_command))
        
        # Add Message Handlers
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        logger.info("🐉 Goku: Telegram bot initialized with Commands + Smart Queue...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"💥 Failed to start Telegram bot: {e}")
