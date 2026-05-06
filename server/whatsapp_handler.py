import logging
import asyncio
from neonize.client import NewClient
from neonize.events import MessageEv
from .agent import agent
from .config import config

logger = logging.getLogger(__name__)

async def start_whatsapp_bot():
    # In a real Lite setup, we might skip the local DB for Neonize if possible, 
    # but for now we'll use a small sqlite file for the session only.
    client = NewClient("goku_lite_wa.db")

    @client.event(MessageEv)
    async def on_message(client, message: MessageEv):
        if message.Message.conversation:
            user_text = message.Message.conversation
            chat_id = message.Info.MessageSource.Chat.String()
            
            logger.info(f"WhatsApp message from {chat_id}: {user_text}")
            
            # Respond to all DMs in Lite mode
            response = await agent.chat(user_text, session_id=f"wa_{chat_id}", source="whatsapp")
            client.send_message(message.Info.MessageSource.Chat, response)

    logger.info("🐉 Goku Lite: WhatsApp bot initializing...")
    # Neonize is synchronous in its connect call usually, or requires a loop.
    # For Lite, we'll assume the user runs this as a background task.
    # Note: WhatsApp requires scanning a QR code on first run.
    client.connect()
