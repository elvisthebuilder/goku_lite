from fastapi import FastAPI, Depends, HTTPException, Header
from server.agent import agent
from server.config import config
from server.telegram_handler import start_telegram_bot
from server.whatsapp_handler import start_whatsapp_bot
import uvicorn
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GokuLite")

app = FastAPI(title="Goku Lite", version="1.0.0")

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

async def start_gateway():
    """Start Telegram/WhatsApp listeners here."""
    logger.info("Goku Lite Gateway active. Listening for cloud events...")
    
    tasks = []
    
    # Start Telegram
    if config.TELEGRAM_BOT_TOKEN:
        tasks.append(start_telegram_bot())
    
    # Start WhatsApp (Optional)
    if os.getenv("ENABLE_WHATSAPP") == "True":
        tasks.append(start_whatsapp_bot())
    
    if tasks:
        await asyncio.gather(*tasks)
    else:
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    config.validate()
    # Run the background gateway
    loop = asyncio.get_event_loop()
    loop.create_task(start_gateway())
    
    # Run the web API
    uvicorn.run(app, host="0.0.0.0", port=8000)
