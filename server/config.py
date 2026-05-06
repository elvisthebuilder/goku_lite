import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM
    GOKU_MODEL = os.getenv("GOKU_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Ollama / Remote
    OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE")
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

    # Memory
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

    # History
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Channels
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    GOKU_OWNER_ID = os.getenv("GOKU_OWNER_ID")

    @classmethod
    def validate(cls):
        """Ensure all required cloud components are configured."""
        missing = []
        if not cls.QDRANT_URL or not cls.QDRANT_API_KEY:
            missing.append("QDRANT_URL/API_KEY")
        if not cls.DATABASE_URL:
            missing.append("DATABASE_URL")
        
        if missing:
            print(f"⚠️  Goku Lite Warning: Missing cloud configuration: {', '.join(missing)}")
            print("Goku will run in 'Limited Mode' (Memory or Logs may be disabled).")

config = Config()
