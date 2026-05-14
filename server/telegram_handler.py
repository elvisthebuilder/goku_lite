import logging
import asyncio
import os
import tempfile
import io
import subprocess
from collections import defaultdict
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from .agent import agent
from .config import config
from .history import history
from .speech_service import transcribe_audio, generate_speech

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
    if not update.message: return

    command = update.message.text.split()[0].lower()
    chat_id = str(update.message.chat_id)
    session_id = f"tg_{chat_id}"

    # Security check
    owner_id = os.getenv("GOKU_OWNER_ID")
    if owner_id and chat_id != owner_id:
        await update.message.reply_text("⚠️ Unauthorized.")
        return

    if command in ["/start", "/new"]:
        history.clear_history(session_id)
        welcome_text = (
            "🐉 *Goku Lite Session Initialized*\n\n"
            "I am GOKU LITE, your elite technical collaborator. "
            "All previous context has been cleared."
        )
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
    elif command == "/status":
        from .scheduler import get_system_report
        ram, disk = await get_system_report()
        status_msg = f"⚡ *System Status Report*\n\nRAM: {ram}\nDisk: {disk}"
        await update.message.reply_text(status_msg, parse_mode="Markdown")
    
    elif command == "/help":
        help_text = "🐉 *Goku Command Center*\n/start - Initialize\n/new - Clear history\n/status - Health check"
        await update.message.reply_text(help_text, parse_mode="Markdown")

def split_message(text, limit=4000):
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1: split_at = limit
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text: chunks.append(text)
    return chunks

async def keep_typing(context, chat_id, stop_event):
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
        except: break

async def process_user_messages(chat_id: str, context: ContextTypes.DEFAULT_TYPE, reply_to_message):
    async with _user_locks[chat_id]:
        messages = _user_message_buffers.pop(chat_id, [])
        if not messages: return

        combined_text = "\n".join(messages)
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(context, chat_id, stop_typing))

        try:
            generator = agent.chat(combined_text, session_id=f"tg_{chat_id}", source="telegram")
            has_response = False
            transient_message = None
            
            async for partial_response in generator:
                if partial_response:
                    has_response = True
                    if partial_response.startswith("⚙️"):
                        if not transient_message:
                            transient_message = await reply_to_message.reply_text(partial_response, parse_mode="Markdown")
                        else:
                            try: await transient_message.edit_text(partial_response, parse_mode="Markdown")
                            except: pass
                    else:
                        if transient_message:
                            try: await transient_message.delete()
                            except: pass
                            transient_message = None
                        
                        # --- Voice Reply Handling ---
                        is_voice_input = any("[Voice Note Transcript]" in m for m in messages)
                        if partial_response.startswith("[VOICE_REPLY]: ") or (is_voice_input and not partial_response.startswith("[")):
                            voice_text = partial_response.replace("[VOICE_REPLY]: ", "").strip()
                            logger.info(f"🎤 [TG] Requesting TTS: {voice_text[:50]}...")
                            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
                            
                            audio_bytes = await generate_speech(voice_text)
                            if audio_bytes:
                                logger.info(f"✅ [TG] TTS Success: {len(audio_bytes)} bytes.")
                                try:
                                    # Convert to ogg via pipe (Stateless)
                                    process = subprocess.Popen(
                                        ["ffmpeg", "-i", "pipe:0", "-c:a", "libopus", "-f", "ogg", "pipe:1"],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                                    )
                                    buff, err = process.communicate(input=audio_bytes)
                                    if buff:
                                        logger.info(f"🎵 [TG] FFmpeg Success: {len(buff)} bytes.")
                                    else:
                                        if err: logger.error(f"❌ [TG] FFmpeg Error: {err.decode()}")
                                    
                                    final_audio = io.BytesIO(buff if buff else audio_bytes)
                                    await reply_to_message.reply_voice(final_audio)
                                except Exception as ve:
                                    logger.error(f"Voice failed: {ve}")
                                    await reply_to_message.reply_text(voice_text)
                            else:
                                await reply_to_message.reply_text(voice_text)

                        # --- Music Reply Handling ---
                        elif partial_response.startswith("[MUSIC_REPLY]: "):
                            music_prompt = partial_response.replace("[MUSIC_REPLY]: ", "").strip()
                            from .speech_service import generate_music
                            music_bytes = await generate_music(music_prompt)
                            if music_bytes:
                                try:
                                    await reply_to_message.reply_audio(io.BytesIO(music_bytes), title="Goku Composition")
                                except Exception as me:
                                    logger.error(f"Music failed: {me}")
                        
                        # --- Standard Text Reply ---
                        else:
                            chunks = split_message(partial_response)
                            for chunk in chunks:
                                try: await reply_to_message.reply_text(chunk, parse_mode="Markdown")
                                except: await reply_to_message.reply_text(chunk)
                            
            stop_typing.set()
            await typing_task
        except Exception as e:
            stop_typing.set()
            logger.error(f"❌ Telegram Error: {e}")
            try: await reply_to_message.reply_text(f"📦 Snag: {str(e)[:100]}")
            except: pass
        finally:
            if not stop_typing.is_set(): stop_typing.set()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    username = update.message.from_user.username or "Unknown"
    
    logger.info(f"📩 Telegram incoming: [{username}] ({chat_id}): {user_text}")
    
    # Auth & Mention logic
    owner_id = os.getenv("GOKU_OWNER_ID")
    if owner_id and chat_id != owner_id and update.message.chat.type == "private":
        logger.warning(f"🚫 Unauthorized access attempt from {chat_id}")
        await update.message.reply_text("⚠️ Access Denied.")
        return

    _user_message_buffers[chat_id].append(user_text)
    if chat_id in _user_timers and not _user_timers[chat_id].done():
        _user_timers[chat_id].cancel()

    async def debounced_process():
        try:
            await asyncio.sleep(DEBOUNCE_SECONDS)
            logger.info(f"🤖 Goku is thinking for {chat_id}...")
            await process_user_messages(chat_id, context, update.message)
        except Exception as de:
            logger.error(f"💥 Debounced Process Error: {de}")

    _user_timers[chat_id] = asyncio.create_task(debounced_process())

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not (update.message.voice or update.message.audio): return
    voice = update.message.voice or update.message.audio
    chat_id = str(update.message.chat_id)
    
    try:
        # For incoming, we still need a temp file for transcription API if it doesn't take bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            new_file = await context.bot.get_file(voice.file_id)
            await new_file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        transcript = await transcribe_audio(tmp_path)
        if os.path.exists(tmp_path): os.remove(tmp_path)

        if transcript:
            user_text = f"[Voice Note Transcript]: {transcript}"
            _user_message_buffers[chat_id].append(user_text)
            # ... trigger debounce ...
            if chat_id in _user_timers and not _user_timers[chat_id].done():
                _user_timers[chat_id].cancel()
            async def debounced_process():
                await asyncio.sleep(DEBOUNCE_SECONDS)
                await process_user_messages(chat_id, context, update.message)
            _user_timers[chat_id] = asyncio.create_task(debounced_process())
    except Exception as e:
        logger.error(f"Voice Error: {e}")

async def start_telegram_bot():
    global _bot_instance
    token = config.TELEGRAM_BOT_TOKEN
    if not token: return
    try:
        application = ApplicationBuilder().token(token).build()
        _bot_instance = application.bot
        application.add_handler(CommandHandler(["start", "new", "status", "help"], handle_command))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
        logger.info("🐉 Goku: Telegram bot initialized (Cloud Native)...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        while True: await asyncio.sleep(3600)
    except Exception as e: logger.error(f"💥 Failed to start Telegram bot: {e}")
