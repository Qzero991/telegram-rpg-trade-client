import logging
from config import settings
from telethon import events
from telegram.tg_client import client
from parser.items_parser import items_info_parser

# ---------------- Logging ----------------
logger = logging.getLogger(__name__)


async def items_listener(items_type_and_id_queue, async_flag):
    """Listens for new item messages and sends them to parser."""

    @client.on(events.NewMessage(chats=settings.items_info_group_id, incoming=True))
    async def items_info_handler(event):
        logger.debug("New message received in items_info_group.")
        await items_info_parser(event, items_type_and_id_queue, async_flag)



