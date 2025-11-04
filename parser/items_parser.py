import config
from config import settings
from telegram.tg_client import client
from database.queries import insert_item_data
from datetime import datetime, timezone
import asyncio
import re



async def items_info_command_printer(items_type_and_id_queue, async_flag):


    for i in range(len(commands)):
        for j in range(0, commands[i][1] + 1):
            items_type_and_id_queue.append({"type":commands[i][2], "in_game_id":j, "datetime":datetime.now(timezone.utc)})
            await client.send_message(settings.items_info_group_id, f"{commands[i][0]} {j}" )
            await asyncio.sleep(1)
            while True:
                try:
                    await asyncio.wait_for(async_flag.wait(), timeout=60)
                    async_flag.clear()
                    if len(items_type_and_id_queue) != 0:
                        await asyncio.sleep(20)
                        items_type_and_id_queue.pop()
                        items_type_and_id_queue.append(
                            {"type": commands[i][2], "in_game_id": j, "datetime": datetime.now(timezone.utc)})
                        await client.send_message(settings.items_info_group_id, f"{commands[i][0]} {j}")

                    else:
                        break
                except asyncio.TimeoutError:
                    if len(items_type_and_id_queue) != 0:
                        print("ДЛИНА ОЧЕРЕДИ ПЕРЕД УДАЛЕНИЕМ: ", len(items_type_and_id_queue))
                        items_type_and_id_queue.pop()
                    items_type_and_id_queue.append(
                        {"type": commands[i][2], "in_game_id": j, "datetime": datetime.now(timezone.utc)})
                    await client.send_message(settings.items_info_group_id, f"{commands[i][0]} {j}")



async def items_info_parser(event, items_type_and_id_queue, async_flag):

    print(event.raw_text)


    if len(items_type_and_id_queue) == 0:
        print("Пустая очередь")
        return


    if  event.raw_text == "⚠️ От вас поступает слишком много сообщений. Действие не будет выполнено.\nНе отправляйте сообщения так часто.":
        async_flag.set()
        return


    data = items_type_and_id_queue.pop()

    if (event.raw_text == "❗️ Экипировка не найдена"
            or event.raw_text == "❗️ Ресурс не найден"
            or "Предмет нельзя передать" in event.raw_text):
        async_flag.set()
        return

    grade = None
    duration = None

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
        elif 'Требуется для изучения навыка' in event.raw_text or 'Требуется для изучения боевого приема' in event.raw_text:
            name_without_split = resource_name_pattern.search(event.raw_text).group(1).strip()
            name_with_split = name_without_split.rsplit(sep=' ', maxsplit=1)
            if len(name_with_split) != 2:
                name = name_without_split
                grade = 'undefined'
            elif len(name_with_split[1]) > 4:
                name = name_without_split
                grade = 'undefined'
            else:
                name, grade = name_with_split
                grade = "[" + grade + "]"

        else:
            name = resource_name_pattern.search(event.raw_text).group(1).strip()
    else:
        print("UNKNOWN ITEM TYPE. items_type_and_id_queue ERROR")
        async_flag.set()
        return



    if not grade:
        grade = grade_pattern.search(event.raw_text).group(1).strip() if grade_pattern.search(event.raw_text) \
            else 'undefined'

    if not duration:
        duration = duration_pattern.search(event.raw_text).group(1).strip() if duration_pattern.search(event.raw_text) \
            else 'undefined'

    temp_duration = duration_in_name_pattern.search(name)

    if temp_duration:
        name = re.sub(duration_in_name_pattern, '', name).strip()

    if duration == 'undefined' and temp_duration:
        duration = temp_duration.group(1).strip()



    data_dict = {
            "item_name":name,
            "item_type":data["type"],
            "item_grade":grade,
            "in_game_id":data["in_game_id"],
            "item_duration":duration
            }

    await insert_item_data(data_dict)



    if name:
        with open("C:\\Users\\alex3\\Desktop\\tg_items_info.txt", "a", encoding="utf-8") as file:
            file.write(
                f"name: {name}\nitem_type: {data['type']}\ngrade: {grade}\nduration: {duration}\ngame_id: {data['in_game_id']}\n\n---------------------\n\n")

    else:
        with open("C:\\Users\\alex3\\Desktop\\unread.txt", "a", encoding="utf-8") as file:
            file.write(
                f"name: {name}\nitem_type: {data['type']}\ngrade: {grade}\nduration: {duration}\ngame_id: {data['in_game_id']}\n\n---------------------\n\n")

    async_flag.set()



# commands = [("/getequip", 871), ("/getasset", 1369)]
commands = [("/getequip", settings.equipment_last_id, "equipment"), ("/getasset", settings.resource_last_id, "resource")]


equip_name_pattern = re.compile(r"Страница экипировки.*?\n[^\n]*?\n.*?([A-Za-zА-Яа-яЁё '’.]+[^\n\[\]\(\)]*)")

resource_name_pattern = re.compile(r"Страница ресурса.*?\n[^\n]*?\n.*?([A-Za-zА-Яа-яЁё0-9 \"'’.%+-]+)")
resource_receipt_name_pattern = re.compile(r"(Рецепт)\s*\[.*?]([^\(\)\n]*)")
resource_potion_name_pattern = re.compile(r"(Зелье)\s*\[.*?]([^\(\)\n]*)")

grade_pattern = re.compile(r'^.*?\n.*?\n.*?(\[[^\]]+\])')


duration_pattern = re.compile(r"Время действия:\s*?([A-Za-zА-Яа-яЁё0-9 ]+)")
duration_in_name_pattern = re.compile(r'\s*(\d+\s*\w+)$')
duration_potion_pattern = re.compile(r"Действие:\s*?([A-Za-zА-Яа-яЁё0-9 ]+)")



