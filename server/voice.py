import logging
from .speech_service import generate_speech

logger = logging.getLogger(__name__)

class VoiceEngine:
    def __init__(self):
        pass

    async def text_to_speech(self, text: str, output_path: str = "response.mp3"):
        """Convert text to speech using the consolidated speech service."""
        return await generate_speech(text, output_path)

voice_engine = VoiceEngine()
