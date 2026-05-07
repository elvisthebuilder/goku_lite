import logging
import asyncio
from neonize.client import NewClient
from neonize.events import MessageEv
from .agent import agent
from .config import config

logger = logging.getLogger(__name__)

async def start_whatsapp_bot():
    """Goku Lite WhatsApp Interface (powered by Neonize)."""
    # Use a small sqlite file for the session only.
    client = NewClient("goku_lite_wa.db")

    @client.event(MessageEv)
    async def on_message(client, message: MessageEv):
        # We only handle text conversations for now
        if message.Message.conversation:
            user_text = message.Message.conversation
            chat_id = message.Info.MessageSource.Chat.String()
            
            logger.info(f"WhatsApp message from {chat_id}: {user_text}")
            
            try:
                # 1. Chat with Agent (using WhatsApp session)
                response = await agent.chat(user_text, session_id=f"wa_{chat_id}", source="whatsapp")
                
                # 2. Silent Turn Handling (OpenClaw standard)
                if response:
                    # WhatsApp doesn't support full Markdown, so we ensure it's clean
                    client.send_message(message.Info.MessageSource.Chat, response)
                else:
                    logger.info(f"Agent is silent for WhatsApp user {chat_id}.")
            except Exception as e:
                logger.error(f"WhatsApp Handler Error: {e}")

    logger.info("🐉 Goku Lite: WhatsApp bot initializing...")
    # Note: On first run, check the console for the QR code to link your account.
    # client.connect() is usually blocking or starts its own loop.
    client.connect()

if __name__ == "__main__":
    asyncio.run(start_whatsapp_bot())
