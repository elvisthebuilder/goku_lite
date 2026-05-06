import os
import logging
from elevenlabs.client import ElevenLabs
from .config import config

logger = logging.getLogger(__name__)

class VoiceEngine:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpg8ndclK7BJb") # Adam
        
        if self.api_key:
            self.client = ElevenLabs(api_key=self.api_key)
        else:
            self.client = None
            logger.info("ElevenLabs API Key missing. Voice output disabled.")

    async def text_to_speech(self, text: str, output_path: str = "response.mp3"):
        """Convert text to speech and save as MP3."""
        if not self.client:
            return None
        
        try:
            # ElevenLabs SDK is synchronous, so we'll run it in a thread
            import asyncio
            def _generate():
                audio = self.client.generate(
                    text=text,
                    voice=self.voice_id,
                    model="eleven_multilingual_v2"
                )
                # Convert generator/iterator to bytes
                content = b"".join(audio)
                with open(output_path, "wb") as f:
                    f.write(content)
                return output_path

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _generate)
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            return None

voice_engine = VoiceEngine()
