import asyncio
import logging

from database.queries import init_db, clear_db_without_items
from logic.processor import message_handler

# Telegram imports
from telegram.group_listener import trade_group_listener
from telegram.tg_client import run_client_forever
from telegram.bot.arbitrage_notification_bot import bot_execution


# Logging setup
logging.basicConfig(
    level=logging.DEBUG,  # change to DEBUG for detailed logs
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

logger.info("Application startup initiated")



# Main application workflow
async def trade_group_message_handler():

    await clear_db_without_items()
    await init_db()

    offer_message_queue = asyncio.Queue()

    # Launch concurrent async tasks
    client_run_task = asyncio.create_task(run_client_forever())
    listener_task = asyncio.create_task(trade_group_listener(offer_message_queue))
    notification_bot_task = asyncio.create_task(bot_execution())

    logger.info("All async tasks launched (client, listener, bot)")

    await message_handler(offer_message_queue)



# Entrypoint
if __name__ == "__main__":
    try:
        logger.info("Starting async event loop...")
        asyncio.run(trade_group_message_handler())
    except KeyboardInterrupt:
        logger.warning("🛑 Application stopped manually (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        logger.info("Application terminated")
