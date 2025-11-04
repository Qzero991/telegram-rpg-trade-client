import asyncio

from telegram.items_info_listener import items_listener
from telegram.group_listener import trade_group_listener
from parser.message_parser import create_request
from parser.items_parser import items_info_command_printer
from telegram.tg_client import client, start_client, run_client_forever
from collections import deque
from rapidfuzz import process, fuzz
from database.models import ItemType, OfferType, CurrencyType
from logic.arbitrage import arbitrage_finder
from database.queries import (get_items, init_db, insert_message_data_and_return_id, drop_arbitrage ,clear_messages,
                              insert_offer_data_and_return_id, drop_messages_table_raw, clear_offers, drop_offers, get_arbitrage_message_item_data_for_bot)
from telegram.bot.arbitrage_notification_bot import main





async def message_handler(offer_message_queue):
    items_in_db = await get_items()

    while True:
        message = await offer_message_queue.get()
        response = await create_request(message.raw_text)
        
        if not response:
            continue

        message_id = await insert_message_data_and_return_id(message)

        if not message_id:
            continue


        await find_foreign_key_item_offer_match_and_insert_offer(items_in_db, response, message_id)





async def find_foreign_key_item_offer_match_and_insert_offer(items_in_db, response, message_id):
    for i in range(len(response)):
        if not isinstance(response[i]["price_for_one"], int):
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
        elif len(top5) >= 2 and top5[0][0] == top5[1][0]:
            print("СООТВЕТСТВУЮЩИЙ ПРЕДМЕТ НЕ НАЙДЕН")
            return

        if not top5:
            return
        elif response[i]['item_duration'] != 'undefined':
            for ind in range(len(top5) - 1, -1, -1):
                if items_in_db[top5[ind][1]].item_duration != response[i]['item_duration']:
                    top5.pop(ind)
        elif len(top5) >= 2 and top5[0][0] == top5[1][0]:
            print("СООТВЕТСТВУЮЩИЙ ПРЕДМЕТ НЕ НАЙДЕН")
            return

        if not top5:
            print("СООТВЕТСТВУЮЩИЙ ПРЕДМЕТ НЕ НАЙДЕН")
        elif top5[0][2] < 80:
            print(top5)
            print("СЛИШКОМ МАЛЕНЬКИЙ ПРОЦЕНТ СОВПАДЕНИЯ, ПРЕДМЕТ НЕ БУДЕТ ДОБАВЛЕН")
        else:
            print(top5)

            offer_data_dict = {
                "id": None,
                "item_name_message": response[i]['item_name'],
                "item_name_db": items_in_db[top5[0][1]].item_name,
                "item_name": items_in_db[top5[0][1]].item_name,
                "item_id": items_in_db[top5[0][1]].id,
                "quantity": response[i]['quantity'],
                "offer_type": OfferType(response[i]['offer_type']),
                "currency": CurrencyType(response[i]['currency']),
                "price_for_one": response[i]['price_for_one'],
                "message_id": message_id
            }

            offer_data_dict['id'] = await insert_offer_data_and_return_id(offer_data_dict)

            if not offer_data_dict['id']:
                continue

            print('ARBITRAGE')

            await arbitrage_finder(offer_data_dict)





async def trade_group_message_handler():
    await clear_messages()
    await drop_messages_table_raw()
    await drop_arbitrage()
    await drop_offers()
    await init_db()
    offer_message_queue = asyncio.Queue()
    client_run_task = asyncio.create_task(run_client_forever())
    listener_task = asyncio.create_task(trade_group_listener(offer_message_queue))
    await message_handler(offer_message_queue)



async def bot_test():
    asyncio.create_task(run_client_forever())
    asyncio.create_task(main())
    await get_arbitrage_message_item_data_for_bot(5)
    # await get_arbitrage_message_item_data_for_bot(3)
    await asyncio.Event().wait()


if __name__ == "__main__":
    # asyncio.run(trade_group_message_handler())
    asyncio.run(bot_test())
















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



