import asyncio
import logging

from database.queries import init_db
from logic.message_processing.message_processor import message_handler
from telegram.bot.arbitrage_notification_bot import bot_execution
from telegram.group_listener import trade_group_listener
from telegram.tg_client import run_client_forever

logger = logging.getLogger(__name__)


# Main application workflow (waits for new messages, extracts offers from each message,
# matches them with items in the database, and searches for arbitrage opportunities.)
async def run_messages_handler():

    # await clear_db_without_items()
    await init_db()

    offer_message_queue = asyncio.Queue()

    # Launch concurrent async tasks
    client_run_task = asyncio.create_task(run_client_forever())
    listener_task = asyncio.create_task(trade_group_listener(offer_message_queue))
    notification_bot_task = asyncio.create_task(bot_execution())

    logger.info("All async tasks launched (client, listener, bot)")

    await message_handler(offer_message_queue)