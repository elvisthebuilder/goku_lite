import logging
import asyncio
import os
import time
import subprocess
import tempfile
from neonize.client import NewClient
from neonize.events import MessageEv
from .agent import agent
from .config import config
from .speech_service import transcribe_audio, generate_speech

logger = logging.getLogger(__name__)

async def start_whatsapp_bot():
    """Goku Lite WhatsApp Interface (powered by Neonize)."""
    # Determine a writable path for the session database
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "goku_lite_wa.db")
    
    try:
        # Check if writable
        test_file = os.path.join(base_dir, ".write_test")
        with open(test_file, "w") as f: f.write("test")
        os.remove(test_file)
    except PermissionError:
        logger.warning("Project directory not writable. Moving session DB to /tmp for Cloud Native fluidity.")
        db_path = os.path.join(tempfile.gettempdir(), "goku_lite_wa.db")
    
    client = NewClient(db_path)

    @client.event(MessageEv)
    async def on_message(client: NewClient, message: MessageEv):
        msg = message.Message
        chat_jid = message.Info.MessageSource.Chat
        session_id = f"wa_{chat_jid.String()}"
        
        user_text = ""
        is_voice = False

        # 1. Detect Content Type
        if msg.conversation:
            user_text = msg.conversation
        elif msg.extendedTextMessage and msg.extendedTextMessage.text:
            user_text = msg.extendedTextMessage.text
        elif msg.audioMessage:
            is_voice = True
            logger.info(f"Incoming voice note from {session_id}...")
            try:
                audio_bytes = client.download_any(msg)
                if audio_bytes:
                    # Transcribe directly from bytes (Cloud Native)
                    transcript = await transcribe_audio(audio_bytes)
                    if transcript:
                        user_text = f"[Voice Note Transcript]: {transcript}"
                    else:
                        user_text = "[Voice Note received but transcription failed]"
            except Exception as e:
                logger.error(f"Failed to process WhatsApp audio: {e}")
                return

        if not user_text:
            return

        logger.info(f"WhatsApp message from {session_id}: {user_text}")

        try:
            # 2. Chat with Agent
            has_response = False
            async for partial_response in agent.chat(user_text, session_id=session_id, source="whatsapp"):
                if not partial_response: continue
                if partial_response.startswith("⚙️"): continue
                
                has_response = True
                
                # --- Voice Reply Handling ---
                if partial_response.startswith("[VOICE_REPLY]: ") or (is_voice and not partial_response.startswith("[")):
                    voice_text = partial_response.replace("[VOICE_REPLY]: ", "").strip()
                    logger.info(f"🎤 Requesting TTS for: {voice_text[:50]}...")
                    audio_bytes = await generate_speech(voice_text)
                    
                    if audio_bytes:
                        logger.info(f"✅ TTS Success: {len(audio_bytes)} bytes received.")
                        try:
                            # Convert to ogg/opus via pipe (Stateless/Diskless)
                            process = subprocess.Popen(
                                ["ffmpeg", "-i", "pipe:0", "-c:a", "libopus", "-f", "ogg", "pipe:1"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                            )
                            buff, err = process.communicate(input=audio_bytes)
                            
                            if buff:
                                logger.info(f"🎵 FFmpeg Success: {len(buff)} bytes converted.")
                            else:
                                if err: logger.error(f"❌ FFmpeg Error: {err.decode()}")
                                logger.warning("⚠️ FFmpeg failed, falling back to raw bytes.")
                                buff = audio_bytes # Fallback to original bytes

                            # Upload and send as AudioMessage (PTT=True)
                            from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import AudioMessage, Message as WAMessage
                            upload_res = client.upload(buff)
                            audio_msg = AudioMessage(
                                URL=upload_res.url,
                                directPath=upload_res.DirectPath,
                                fileEncSHA256=upload_res.FileEncSHA256,
                                fileLength=upload_res.FileLength,
                                fileSHA256=upload_res.FileSHA256,
                                mediaKey=upload_res.MediaKey,
                                mimetype="audio/ogg; codecs=opus",
                                PTT=True
                            )
                            client.send_message(chat_jid, WAMessage(audioMessage=audio_msg))
                        except Exception as ve:
                            logger.error(f"Voice reply delivery failed: {ve}")
                            client.send_message(chat_jid, voice_text)
                    else:
                        client.send_message(chat_jid, voice_text)
                
                # --- Music Reply Handling ---
                elif partial_response.startswith("[MUSIC_REPLY]: "):
                    # The tool now returns the prompt or a temporary path. 
                    # For Cloud Native, we'll assume it's a request to generate bytes.
                    music_prompt = partial_response.replace("[MUSIC_REPLY]: ", "").strip()
                    from .speech_service import generate_music
                    music_bytes = await generate_music(music_prompt)
                    
                    if music_bytes:
                        try:
                            from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import AudioMessage, Message as WAMessage
                            upload_res = client.upload(music_bytes)
                            audio_msg = AudioMessage(
                                URL=upload_res.url,
                                directPath=upload_res.DirectPath,
                                fileEncSHA256=upload_res.FileEncSHA256,
                                fileLength=upload_res.FileLength,
                                fileSHA256=upload_res.FileSHA256,
                                mediaKey=upload_res.MediaKey,
                                mimetype="audio/mpeg",
                                PTT=False
                            )
                            client.send_message(chat_jid, WAMessage(audioMessage=audio_msg))
                        except Exception as me:
                            logger.error(f"Music delivery failed: {me}")
                
                # --- Standard Text Reply ---
                else:
                    client.send_message(chat_jid, partial_response)
                        
            if not has_response:
                logger.info(f"Agent is silent for WhatsApp user {session_id}.")
        except Exception as e:
            logger.error(f"WhatsApp Handler Error: {e}")

    logger.info("🐉 Goku Lite: WhatsApp bot initializing (Cloud Native mode)...")
    client.connect()

if __name__ == "__main__":
    asyncio.run(start_whatsapp_bot())
