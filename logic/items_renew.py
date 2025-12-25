import logging
import asyncio
from config import settings
from collections import deque
from telegram.items_info_listener import items_listener
from logic.commands_printer import items_info_command_printer
from telegram.tg_client import start_client, run_client_forever

logger = logging.getLogger(__name__)

# Renews table 'Items' in db, by printing commands and analyzing answers from game_info_bot
async def items_in_file_renew():

    logger.info("Items data renewal in database started")

    clear_file()
    items_type_and_id_queue = deque(maxlen=1)
    async_flag = asyncio.Event()
    # await init_db()
    await start_client()
    await items_listener(items_type_and_id_queue, async_flag)
    asyncio.create_task(items_info_command_printer(items_type_and_id_queue, async_flag))
    await run_client_forever()


def clear_file():
    with open(settings.file_path, "w", encoding="utf-8") as file:
        print("ok")
