import logging
import asyncio
import os
import time
from neonize.client import NewClient
from neonize.events import MessageEv
from .agent import agent
from .config import config
from .speech_service import transcribe_audio, generate_speech

logger = logging.getLogger(__name__)

async def start_whatsapp_bot():
    """Goku Lite WhatsApp Interface (powered by Neonize)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.join(base_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Use a small sqlite file for the session only.
    db_path = os.path.join(base_dir, "goku_lite_wa.db")
    client = NewClient(db_path)

    @client.event(MessageEv)
    async def on_message(client: NewClient, message: MessageEv):
        msg = message.Message
        chat_jid = message.Info.MessageSource.Chat
        session_id = f"wa_{chat_jid.String()}"
        
        user_text = ""
        is_voice = False
        attachment_path = None

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
                    ts = int(time.time())
                    attachment_path = os.path.join(uploads_dir, f"wa_v_{ts}.ogg")
                    with open(attachment_path, "wb") as f:
                        f.write(audio_bytes)
                    
                    # Transcribe
                    transcript = await transcribe_audio(attachment_path)
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
                if not partial_response:
                    continue
                
                if partial_response.startswith("⚙️"):
                    continue
                
                has_response = True
                
                # --- Voice Reply Handling ---
                if partial_response.startswith("[VOICE_REPLY]: ") or (is_voice and not partial_response.startswith("[")):
                    voice_text = partial_response.replace("[VOICE_REPLY]: ", "").strip()
                    ts = int(time.time())
                    rp = os.path.join(uploads_dir, f"wa_r_{ts}.mp3")
                    op = os.path.join(uploads_dir, f"wa_r_{ts}.ogg")
                    
                    if await generate_speech(voice_text, rp):
                        try:
                            # Convert to ogg/opus for WhatsApp PTT compatibility
                            import subprocess
                            subprocess.run(["ffmpeg", "-y", "-i", rp, "-c:a", "libopus", op], 
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            
                            fpath = op if os.path.exists(op) else rp
                            with open(fpath, "rb") as af:
                                buff = af.read()
                            
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
                        finally:
                            for p in [rp, op]:
                                if os.path.exists(p): os.remove(p)
                    else:
                        client.send_message(chat_jid, voice_text)
                
                # --- Music Reply Handling ---
                elif partial_response.startswith("[MUSIC_REPLY]: "):
                    rel_path = partial_response.replace("[MUSIC_REPLY]: ", "").strip()
                    music_path = os.path.join(base_dir, rel_path)
                    if os.path.exists(music_path):
                        try:
                            with open(music_path, "rb") as mf:
                                buff = mf.read()
                            from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import AudioMessage, Message as WAMessage
                            upload_res = client.upload(buff)
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

    logger.info("🐉 Goku Lite: WhatsApp bot initializing...")
    client.connect()

if __name__ == "__main__":
    asyncio.run(start_whatsapp_bot())
