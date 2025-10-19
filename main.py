import asyncio
from typing import List, Optional, Tuple

from telegram.items_info_listener import items_listener
from telegram.group_listener import trade_group_listener
from parser.message_parser import create_request
from parser.items_parser import items_info_command_printer
from telegram.tg_client import client, start_client, run_client_forever
from database.queries import init_db, get_items
from collections import deque
from rapidfuzz import process, fuzz
from database.queries import insert_message_data, insert_item_data, clear_messages, insert_offer_data, drop_messages_table_raw, clear_offers, drop_offers
from database.models import ItemType




async def message_handler(offer_message_queue):
    items_in_db = await get_items()

    while True:
        message = await offer_message_queue.get()
        message_id = await insert_message_data(message)
        if not message_id:
            continue
        response = await create_request(message.raw_text)
        if not response:
            continue
        await find_foreign_key_item_offer_match_and_insert_offer(items_in_db, response, message_id)





async def find_foreign_key_item_offer_match_and_insert_offer(items_in_db, response, message_id):
    for i in range(len(response)):
        if isinstance(response[i]["price_for_one"], int):
            continue
        top5 = [None] * 5
        for j in range(len(items_in_db)):

            ratio_score = fuzz.ratio(response[i]['item_name'].lower(), items_in_db[j].item_name.lower())
            partial_score = fuzz.partial_ratio(response[i]['item_name'].lower(), items_in_db[j].item_name.lower())
            current_score = (ratio_score * 0.4 + partial_score * 0.6)
            temp = (items_in_db[j].item_name, j, current_score)

            for k in range(len(top5)):
                if not top5[k]:
                    top5[k] = temp
                    break
                elif current_score > top5[k][2]:
                    for l in range(k, len(top5)):
                        temp, top5[l] = top5[l], temp
                    break
        print(top5)
        if response[i]['item_grade'] != 'undefined':
            for ind in range(len(top5) - 1, -1, -1):
                if items_in_db[top5[ind][1]].item_grade != response[i]['item_grade']:
                    top5.pop(ind)

        if response[i]['item_duration'] != 'undefined':
            for ind in range(len(top5) - 1, -1, -1):
                if items_in_db[top5[ind][1]].item_duration != response[i]['item_duration']:
                    top5.pop(ind)

        if not top5:
            print("СООТВЕТСТВУЮЩИЙ ПРЕДМЕТ НЕ НАЙДЕН")
        elif top5[0][2] < 80:
            print(top5)
            print("СЛИШКОМ МАЛЕНЬКИЙ ПРОЦЕНТ СОВПАДЕНИЯ, ПРЕДМЕТ НЕ БУДЕТ ДОБАВЛЕН")
        else:
            print(top5)
            await insert_offer_data(response[i], items_in_db[top5[0][1]].id, message_id)



async def trade_group_message_handler():
    # await drop_offers()
    # await drop_messages_table_raw()
    await clear_messages()
    await init_db()
    offer_message_queue = asyncio.Queue()
    client_run_task = asyncio.create_task(run_client_forever())
    listener_task = asyncio.create_task(trade_group_listener(offer_message_queue))
    await message_handler(offer_message_queue)




asyncio.run(trade_group_message_handler())
















async def items_in_file_renew():
    clear_file()
    items_type_and_id_queue = deque(maxlen=1)
    async_flag = asyncio.Event()
    # await init_db()
    await start_client()
    await items_listener(items_type_and_id_queue, async_flag)
    asyncio.create_task(items_info_command_printer(items_type_and_id_queue, async_flag))
    await run_client_forever()


def clear_file():
    with open("C:\\Users\\alex3\\Desktop\\tg_items_info.txt", "w", encoding="utf-8") as file:
        print("ok")

# async def test():
#     await clear_offers()
#     await drop_offers()
#


def test_fuzz():
    str1 = 'Талант - Оракул'
    str2 = 'Талант - Оракул'
    str3 = '14 дней'
    str4 = '7 дней'
    str5 = '15 дней'
    str6 = '24 часа'
    str7 = '24ч'
    print(fuzz.partial_ratio(str1.lower(), str2.lower()))
    print(fuzz.ratio(str1.lower(), str2.lower()))
    print(fuzz.ratio(str6, str7))
    print(fuzz.ratio(str6, str1))

