from fastapi import FastAPI, Depends, HTTPException, Header
import uvicorn
import asyncio
import logging
import os
import sys
import subprocess
from contextlib import asynccontextmanager

# Get the absolute path to the directory where this script is located
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")

from dotenv import load_dotenv
load_dotenv(env_path)

# Guard: Ensure configuration exists before loading other modules
if not os.path.exists(env_path) or not os.getenv("GOKU_MODEL"):
    print("🐉 Goku Lite: Missing configuration. Launching Onboarding Wizard...")
    try:
        setup_script = os.path.join(base_dir, "setup.py")
        subprocess.run([sys.executable, setup_script], check=True)
        load_dotenv(env_path, override=True)
    except Exception as e:
        print(f"❌ Failed to launch onboarding: {e}")
        sys.exit(1)

# Now we can safely import components that depend on config
from server.agent import agent
from server.config import config
from server.telegram_handler import start_telegram_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GokuLite")

async def start_gateway():
    """Start Telegram/WhatsApp listeners here."""
    logger.info("Goku Lite Gateway active. Listening for cloud events...")
    
    tasks = []
    
    # Start Telegram
    if config.TELEGRAM_BOT_TOKEN:
        tasks.append(start_telegram_bot())
    
    # Start WhatsApp (Optional)
    if os.getenv("ENABLE_WHATSAPP") == "True":
        from server.whatsapp_handler import start_whatsapp_bot
        tasks.append(start_whatsapp_bot())
    
    if tasks:
        await asyncio.gather(*tasks)
    else:
        while True: await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background gateway
    gateway_task = asyncio.create_task(start_gateway())
    yield
    # Shutdown: Cancel the gateway task
    gateway_task.cancel()
    try:
        await gateway_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Goku Lite", version="1.0.0", lifespan=lifespan)

def verify_token(x_token: str = Header(None)):
    secret = os.getenv("API_SECRET_KEY")
    if secret and x_token != secret:
        raise HTTPException(status_code=403, detail="Invalid API Secret Key")

@app.get("/")
async def root():
    return {"message": "Goku Lite is ONLINE", "mode": "Cloud-Native"}

@app.get("/health", dependencies=[Depends(verify_token)])
async def health():
    return {
        "llm": config.GOKU_MODEL,
        "db": "connected" if config.DATABASE_URL else "local",
        "memory": "active" if config.QDRANT_API_KEY else "inactive"
    }

@app.post("/chat")
async def chat(text: str, session_id: str = "default"):
    response = await agent.chat(text, session_id)
    return {"response": response}

if __name__ == "__main__":
    config.validate()
    # Run the web API (Lifespan handles the gateway)
    uvicorn.run(app, host="0.0.0.0", port=8000)
