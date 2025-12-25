import asyncio
import logging
from datetime import datetime, timezone

from config import settings
from telegram.tg_client import client

logger = logging.getLogger(__name__)


commands = [
    ("/getequip", settings.equipment_last_id, "equipment"),
    ("/getasset", settings.resource_last_id, "resource")
]

# Sends item info commands to telegram game_info_bot in sequence, handling rate limits and retries.
async def items_info_command_printer(items_type_and_id_queue, async_flag):

    logger.info("Starting item info command printer...")

    for cmd, limit, item_type in commands:
        logger.info(f"Processing command {cmd} up to ID {limit}")

        for item_id in range(limit + 1):
            # add current task to queue
            items_type_and_id_queue.append({
                "type": item_type,
                "in_game_id": item_id,
                "datetime": datetime.now(timezone.utc)
            })

            await client.send_message(settings.items_info_group_id, f"{cmd} {item_id}")
            await asyncio.sleep(1)

            # wait for response signal
            while True:
                try:
                    await asyncio.wait_for(async_flag.wait(), timeout=60)
                    async_flag.clear()

                    if len(items_type_and_id_queue) != 0:
                        await asyncio.sleep(20)
                        items_type_and_id_queue.pop()
                        items_type_and_id_queue.append({
                            "type": item_type,
                            "in_game_id": item_id,
                            "datetime": datetime.now(timezone.utc)
                        })
                        await client.send_message(settings.items_info_group_id, f"{cmd} {item_id}")
                    else:
                        break

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout for {cmd} {item_id}, retrying...")
                    if len(items_type_and_id_queue) != 0:
                        logger.debug(f"Queue size before pop: {len(items_type_and_id_queue)}")
                        items_type_and_id_queue.pop()

                    items_type_and_id_queue.append({
                        "type": item_type,
                        "in_game_id": item_id,
                        "datetime": datetime.now(timezone.utc)
                    })
                    await client.send_message(settings.items_info_group_id, f"{cmd} {item_id}")

    logger.info("Item info command printer finished.")