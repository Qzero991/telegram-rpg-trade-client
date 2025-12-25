import logging
import re
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



# Parses incoming Telegram messages and extracts item info to store in DB.
async def items_info_parser(event, items_type_and_id_queue, async_flag):

    text = event.raw_text
    logger.debug(f"Received message: {event.raw_text[:100]}...")

    if not items_type_and_id_queue:
        logger.warning("Queue is empty — skipping message.")
        return

    # Telegram anti-spam warning
    if is_rate_limit_message(text):
        logger.warning("Rate limit triggered — waiting before retry.")
        async_flag.set()
        return

    data = items_type_and_id_queue.pop()

    # Messages that mean item not found or not transferable
    if is_item_not_found(text):
        logger.debug("Item not found or not transferable.")
        async_flag.set()
        return

    name, grade, duration = parse_name_grade_duration(data['type'], text)

    if not name:
        logger.error("Unknown item type or regex mismatch.")
        async_flag.set()
        return

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


def is_rate_limit_message(text):
    return text ==(
        "⚠️ От вас поступает слишком много сообщений. Действие не будет выполнено.\n"
        "Не отправляйте сообщения так часто."
    )


def is_item_not_found(text):
    return (
        text == "❗️ Экипировка не найдена"
        or text == "❗️ Ресурс не найден"
        or "Предмет нельзя передать" in text
    )


def parse_name_grade_duration(item_type, text):
    name = None
    grade = None
    duration = None

    # Name
    if item_type == 'equipment':
        match = equip_name_pattern.search(text)
        if match:
            name = match.group(1).strip()

    elif item_type == 'resource':
        match = resource_name_pattern.search(text)
        if not match:
            return None, None, None

        base_name = match.group(1).strip()

        if base_name == 'Рецепт':
            m = resource_receipt_name_pattern.search(text)
            name = (m.group(1) + m.group(2)).strip()

        elif base_name == 'Зелье':
            m = resource_potion_name_pattern.search(text)
            name = (m.group(1) + m.group(2)).strip()
            duration = duration_potion_pattern.search(text).group(1).strip()

        elif (
            'Требуется для изучения навыка' in text
            or 'Требуется для изучения боевого приема' in text
        ):
            name_with_split = base_name.rsplit(sep=' ', maxsplit=1)
            if len(name_with_split) != 2 or len(name_with_split[1]) > 4:
                name = base_name
                grade = 'undefined'
            else:
                name, grade = name_with_split
                grade = "[" + grade + "]"
        else:
            name = base_name

    # Grade
    if grade is None:
        m = grade_pattern.search(text)
        grade = m.group(1).strip() if m else "undefined"

    # Duration
    if duration is None:
        m = duration_pattern.search(text)
        duration = m.group(1).strip() if m else "undefined"

    # Check duration in name
    temp_duration = duration_in_name_pattern.search(name)
    if temp_duration:
        name = re.sub(duration_in_name_pattern, '', name).strip()

    if duration == 'undefined' and temp_duration:
        duration = temp_duration.group(1).strip()

    return name, grade, duration
