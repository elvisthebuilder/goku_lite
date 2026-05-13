import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # Base settings from .env
        self.GOKU_MODEL = os.getenv("GOKU_MODEL", "gpt-4o-mini")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE")
        self.OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
        self.QDRANT_URL = os.getenv("QDRANT_URL")
        self.QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.GOKU_OWNER_ID = os.getenv("GOKU_OWNER_ID")
        self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
        self.ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpg8ndclK7BJb")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        
        # Scheduler defaults (Only managed via goku_settings.json now)
        self.BRIEFING_HOUR = 8
        self.BRIEFING_MINUTE = 0
        self.AFTERNOON_HOUR = 14
        self.AFTERNOON_MINUTE = 0
        self.EVENING_HOUR = 20
        self.EVENING_MINUTE = 0

        # Load autonomous overrides
        self._load_overrides()

    def _load_overrides(self):
        """Load settings from goku_settings.json if it exists."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            settings_path = os.path.join(base_dir, "goku_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    overrides = json.load(f)
                    self.BRIEFING_HOUR = overrides.get("briefing_hour", self.BRIEFING_HOUR)
                    self.BRIEFING_MINUTE = overrides.get("briefing_minute", self.BRIEFING_MINUTE)
                    self.AFTERNOON_HOUR = overrides.get("afternoon_hour", self.AFTERNOON_HOUR)
                    self.AFTERNOON_MINUTE = overrides.get("afternoon_minute", self.AFTERNOON_MINUTE)
                    self.EVENING_HOUR = overrides.get("evening_hour", self.EVENING_HOUR)
                    self.EVENING_MINUTE = overrides.get("evening_minute", self.EVENING_MINUTE)
        except Exception:
            pass

    def validate(self):
        """Ensure all required cloud components are configured."""
        missing = []
        if not self.QDRANT_URL or not self.QDRANT_API_KEY:
            missing.append("QDRANT_URL/API_KEY")
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        
        if missing:
            print(f"⚠️  Goku Lite Warning: Missing cloud configuration: {', '.join(missing)}")
            print("Goku will run in 'Limited Mode' (Memory or Logs may be disabled).")

config = Config()
