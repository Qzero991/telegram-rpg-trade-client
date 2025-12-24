import logging
import asyncio
import re
from datetime import datetime, timezone
from config import settings
from telegram.tg_client import client
from database.queries import insert_item_data

# Logging
logger = logging.getLogger(__name__)

# Patterns
equip_name_pattern = re.compile(r"Страница экипировки.*?\n[^\n]*?\n.*?([A-Za-zА-Яа-яЁё '’.]+[^\n\[\]\(\)]*)")
resource_name_pattern = re.compile(r"Страница ресурса.*?\n[^\n]*?\n.*?([A-Za-zА-Яа-яЁё0-9 \"'’.%+-]+)")
resource_receipt_name_pattern = re.compile(r"(Рецепт)\s*\[.*?]([^\(\)\n]*)")
resource_potion_name_pattern = re.compile(r"(Зелье)\s*\[.*?]([^\(\)\n]*)")
grade_pattern = re.compile(r'^.*?\n.*?\n.*?(\[[^\]]+\])')
duration_pattern = re.compile(r"Время действия:\s*?([A-Za-zА-Яа-яЁё0-9 ]+)")
duration_in_name_pattern = re.compile(r'\s*(\d+\s*\w+)$')
duration_potion_pattern = re.compile(r"Действие:\s*?([A-Za-zА-Яа-яЁё0-9 ]+)")
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

# Parses incoming Telegram messages and extracts item info to store in DB.
async def items_info_parser(event, items_type_and_id_queue, async_flag):

    logger.debug(f"Received message: {event.raw_text[:100]}...")

    if len(items_type_and_id_queue) == 0:
        logger.warning("Queue is empty — skipping message.")
        return

    # Telegram anti-spam warning
    if event.raw_text == (
        "⚠️ От вас поступает слишком много сообщений. Действие не будет выполнено.\n"
        "Не отправляйте сообщения так часто."
    ):
        logger.warning("Rate limit triggered — waiting before retry.")
        async_flag.set()
        return

    data = items_type_and_id_queue.pop()

    # messages that mean item not found or not transferable
    if (
        event.raw_text == "❗️ Экипировка не найдена"
        or event.raw_text == "❗️ Ресурс не найден"
        or "Предмет нельзя передать" in event.raw_text
    ):
        logger.debug("Item not found or not transferable.")
        async_flag.set()
        return

    grade = None
    duration = None

    # parse item name
    if data['type'] == 'equipment' and equip_name_pattern.search(event.raw_text):
        name = equip_name_pattern.search(event.raw_text).group(1).strip()

    elif data['type'] == 'resource' and resource_name_pattern.search(event.raw_text):
        if resource_name_pattern.search(event.raw_text).group(1).strip() == 'Рецепт':
            match = resource_receipt_name_pattern.search(event.raw_text)
            name = (match.group(1) + match.group(2)).strip()
        elif resource_name_pattern.search(event.raw_text).group(1).strip() == 'Зелье':
            match = resource_potion_name_pattern.search(event.raw_text)
            name = (match.group(1) + match.group(2)).strip()
            duration = duration_potion_pattern.search(event.raw_text).group(1).strip()
        elif (
            'Требуется для изучения навыка' in event.raw_text
            or 'Требуется для изучения боевого приема' in event.raw_text
        ):
            name_without_split = resource_name_pattern.search(event.raw_text).group(1).strip()
            name_with_split = name_without_split.rsplit(sep=' ', maxsplit=1)
            if len(name_with_split) != 2 or len(name_with_split[1]) > 4:
                name = name_without_split
                grade = 'undefined'
            else:
                name, grade = name_with_split
                grade = "[" + grade + "]"
        else:
            name = resource_name_pattern.search(event.raw_text).group(1).strip()

    else:
        logger.error("Unknown item type or regex mismatch.")
        async_flag.set()
        return

    # parse grade/duration
    if not grade:
        grade = grade_pattern.search(event.raw_text).group(1).strip() if grade_pattern.search(event.raw_text) else 'undefined'

    if not duration:
        duration = duration_pattern.search(event.raw_text).group(1).strip() if duration_pattern.search(event.raw_text) else 'undefined'

    # check duration in name
    temp_duration = duration_in_name_pattern.search(name)
    if temp_duration:
        name = re.sub(duration_in_name_pattern, '', name).strip()

    if duration == 'undefined' and temp_duration:
        duration = temp_duration.group(1).strip()

    data_dict = {
        "item_name": name,
        "item_type": data["type"],
        "item_grade": grade,
        "in_game_id": data["in_game_id"],
        "item_duration": duration
    }

    # insert parsed item into DB
    try:
        await insert_item_data(data_dict)
        logger.info(f"Item inserted: {name} ({grade})")
    except Exception as e:
        logger.error(f"Failed to insert item {name}: {e}")

    async_flag.set()
