import logging
from config import settings
from telethon import events
from telegram.tg_client import client

# ---------------- Logging ----------------
logger = logging.getLogger(__name__)


async def trade_group_listener(offer_message_queue=None):
    """Listens for new trade messages and adds them to queue."""

    @client.on(events.NewMessage(chats=settings.trade_group_id, incoming=True, outgoing=True))
    async def group_handler(event):
        logger.debug(f"New trade message received: {event.raw_text[:100]}")  # Logging only first 100 symbols
        await offer_message_queue.put(event)
