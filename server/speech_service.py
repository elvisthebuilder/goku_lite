import os
import httpx
import logging
from typing import Optional
from .config import config

logger = logging.getLogger(__name__)

# Constants
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_SOUNDS_URL = "https://api.elevenlabs.io/v1/sound-generation"
ELEVENLABS_MUSIC_URL = "https://api.elevenlabs.io/v1/music/compose"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

async def transcribe_audio(file_path: str) -> Optional[str]:
    """
    Transcribe an audio file using ElevenLabs (Scribe), Groq (Whisper), or OpenAI.
    Gracefully returns None if no STT keys are configured.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")

    if not groq_api_key and not openai_api_key and not elevenlabs_key:
        logger.info("Speech-to-Text requested, but no valid API keys found. Skipping transcription.")
        return None

    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        return None

    # Prefer ElevenLabs (Scribe) > Groq > OpenAI
    provider = "elevenlabs"
    if elevenlabs_key:
        url = ELEVENLABS_STT_URL
        headers = {"xi-api-key": elevenlabs_key}
        model = "scribe_v1"
    elif groq_api_key:
        provider = "groq"
        url = GROQ_STT_URL
        headers = {"Authorization": f"Bearer {groq_api_key}"}
        model = "whisper-large-v3"
    else:
        provider = "openai"
        url = OPENAI_STT_URL
        headers = {"Authorization": f"Bearer {openai_api_key}"}
        model = "whisper-1"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                data = {"model_id": model} if provider == "elevenlabs" else {"model": model}
                
                response = await client.post(url, headers=headers, files=files, data=data)
                
                if response.status_code == 200:
                    return response.json().get("text")
                else:
                    logger.error(f"STT API ({provider}) failed [{response.status_code}]: {response.text}")
                    return None
                    
    except Exception as e:
        logger.error(f"Failed to transcribe audio via {provider}: {e}")
        return None

async def generate_speech(text: str, output_path: str) -> bool:
    """
    Generate speech from text using ElevenLabs.
    """
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", config.ELEVENLABS_VOICE_ID)

    if not elevenlabs_key:
        logger.info("Text-to-Speech requested, but no ELEVENLABS_API_KEY found.")
        return False

    url = f"{ELEVENLABS_TTS_URL}/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": elevenlabs_key
    }
    
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, headers=headers, json=data) as response:
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                    return True
                else:
                    error_msg = await response.aread()
                    logger.error(f"ElevenLabs API failed ({response.status_code}): {error_msg.decode('utf-8')}")
                    return False
    except Exception as e:
        logger.error(f"Failed to generate speech: {e}")
        return False

async def generate_music(prompt: str, output_path: str) -> bool:
    """Generate music from a prompt using ElevenLabs."""
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    if not elevenlabs_key: return False

    headers = {"xi-api-key": elevenlabs_key, "Content-Type": "application/json"}
    data = {"prompt": prompt, "music_length_ms": 30000}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", ELEVENLABS_MUSIC_URL, headers=headers, json=data) as response:
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                    return True
        return False
    except Exception as e:
        logger.error(f"Music generation error: {e}")
        return False
