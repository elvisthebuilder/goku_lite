import os
import httpx
import logging
from typing import Optional, Union
from .config import config

logger = logging.getLogger(__name__)

# Constants
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_SOUNDS_URL = "https://api.elevenlabs.io/v1/sound-generation"
ELEVENLABS_MUSIC_URL = "https://api.elevenlabs.io/v1/music/compose"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

async def transcribe_audio(audio_data: Union[str, bytes]) -> Optional[str]:
    """
    Transcribe an audio file or raw bytes using ElevenLabs, Groq, or OpenAI.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")

    if not groq_api_key and not openai_api_key and not elevenlabs_key:
        logger.info("Speech-to-Text requested, but no valid API keys found.")
        return None

    # Resolve provider
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
            if isinstance(audio_data, str):
                if not os.path.exists(audio_data): return None
                with open(audio_data, "rb") as f: content = f.read()
                filename = os.path.basename(audio_data)
            else:
                content = audio_data
                filename = "audio.ogg"

            files = {"file": (filename, content, "application/octet-stream")}
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

async def generate_speech(text: str, output_path: Optional[str] = None) -> Union[bool, bytes]:
    """
    Generate speech from text. Returns True/False if output_path is provided, 
    otherwise returns raw audio bytes.
    """
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", config.ELEVENLABS_VOICE_ID)

    if not elevenlabs_key:
        logger.info("Text-to-Speech requested, but no ELEVENLABS_API_KEY found.")
        return False if output_path else None

    url = f"{ELEVENLABS_TTS_URL}/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": elevenlabs_key}
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            
            # FALLBACK LOGIC: If configured voice is missing, fetch first available voice
            if response.status_code == 404 and "voice_not_found" in response.text:
                logger.warning(f"Voice ID {voice_id} not found. Attempting fallback to first available voice...")
                list_url = "https://api.elevenlabs.io/v1/voices"
                list_resp = await client.get(list_url, headers={"xi-api-key": elevenlabs_key})
                if list_resp.status_code == 200:
                    voices = list_resp.json().get("voices", [])
                    if voices:
                        fallback_id = voices[0]["voice_id"]
                        logger.info(f"Using fallback voice: {voices[0]['name']} ({fallback_id})")
                        # Retry with fallback
                        fallback_url = f"{ELEVENLABS_TTS_URL}/{fallback_id}"
                        response = await client.post(fallback_url, headers=headers, json=data)

            if response.status_code == 200:
                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return True
                return response.content
            else:
                logger.error(f"ElevenLabs API failed ({response.status_code}): {response.text}")
                return False if output_path else None
    except Exception as e:
        logger.error(f"Failed to generate speech: {e}")
        return False if output_path else None

async def generate_music(prompt: str, output_path: Optional[str] = None) -> Union[bool, bytes]:
    """Generate music from a prompt. Returns True/False if output_path provided, else bytes."""
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    if not elevenlabs_key: return False if output_path else None

    headers = {"xi-api-key": elevenlabs_key, "Content-Type": "application/json"}
    data = {"prompt": prompt, "music_length_ms": 30000}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(ELEVENLABS_MUSIC_URL, headers=headers, json=data)
            if response.status_code == 200:
                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return True
                return response.content
            else:
                logger.error(f"ElevenLabs Music API failed ({response.status_code}): {response.text}")
                return False if output_path else None
    except Exception as e:
        logger.error(f"Music generation error: {e}")
        return False if output_path else None
