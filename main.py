import asyncio
import logging
from rapidfuzz import fuzz

# Telegram & project imports
from telegram.group_listener import trade_group_listener
from telegram.tg_client import run_client_forever
from telegram.bot.arbitrage_notification_bot import bot_execution
from parser.message_parser import create_request
from logic.arbitrage import arbitrage_finder
from database.models import OfferType, CurrencyType
from database.queries import (
    get_items, init_db, insert_message_data_and_return_id,
    drop_arbitrage, clear_messages, insert_offer_data_and_return_id,
    drop_messages_table_raw, drop_offers
)

# =====================================================
# Logging setup
# =====================================================
logging.basicConfig(
    level=logging.INFO,  # change to DEBUG for detailed logs
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

logger.info("Application startup initiated")


# =====================================================
# Message processing: parse, validate, and save to DB
# =====================================================
async def message_handler(offer_message_queue):
    items_in_db = await get_items()
    logger.info(f"Loaded {len(items_in_db)} items from database")

    while True:
        message = await offer_message_queue.get()
        logger.info(f"New message received: {message.raw_text}...")

        response = await create_request(message.raw_text)
        if not response:
            logger.debug("Message ignored — no valid parsed data")
            continue

        message_id = await insert_message_data_and_return_id(message)
        if not message_id:
            logger.warning("Message insertion failed — skipping")
            continue

        await find_foreign_key_item_offer_match_and_insert_offer(items_in_db, response, message_id)


# =====================================================
# Offer-item match + insertion logic
# =====================================================
async def find_foreign_key_item_offer_match_and_insert_offer(items_in_db, response, message_id):
    for entry in response:
        if not isinstance(entry["price_for_one"], int):
            logger.debug(f"Skipping — invalid price: {entry['price_for_one']}")
            continue

        top5 = [None] * 5

        # --- Find top 5 similar items ---
        for j, db_item in enumerate(items_in_db):
            ratio_score = fuzz.ratio(entry['item_name'].lower(), db_item.item_name.lower())
            partial_score = fuzz.partial_ratio(entry['item_name'].lower(), db_item.item_name.lower())
            current_score = (ratio_score * 0.4 + partial_score * 0.6)
            candidate = (db_item.item_name, j, current_score)

            for k in range(len(top5)):
                if not top5[k]:
                    top5[k] = candidate
                    break
                elif current_score > top5[k][2]:
                    for l in range(k, len(top5)):
                        candidate, top5[l] = top5[l], candidate
                    break

        logger.debug(f"Top 5 matches for '{entry['item_name']}': {top5}")

        # --- Filter by grade ---
        if entry['item_grade'] != 'undefined':
            top5 = [x for x in top5 if x and items_in_db[x[1]].item_grade == entry['item_grade']]
        elif len(top5) >= 2 and top5[0][0] == top5[1][0]:
            logger.warning(f"No unique match found for item: {entry['item_name']}")
            continue

        if not top5:
            logger.warning(f"No match found for: {entry['item_name']}")
            continue

        # --- Filter by duration ---
        if entry['item_duration'] != 'undefined':
            top5 = [x for x in top5 if x and items_in_db[x[1]].item_duration == entry['item_duration']]
        elif len(top5) >= 2 and top5[0][0] == top5[1][0]:
            logger.warning(f"No unique duration match for item: {entry['item_name']}")
            continue

        if not top5:
            logger.warning(f"No valid match found for: {entry['item_name']}")
            continue

        best_match = top5[0]
        if best_match[2] < 80:
            logger.info(f"Low match score ({best_match[2]:.1f}%) — item not inserted: {entry['item_name']}")
            continue

        db_item = items_in_db[best_match[1]]
        logger.info(f"Matched '{entry['item_name']}' → '{db_item.item_name}' ({best_match[2]:.1f}%)")

        # --- Prepare and insert offer data ---
        offer_data = {
            "id": None,
            "item_name_message": entry['item_name'],
            "item_name_db": db_item.item_name,
            "item_name": db_item.item_name,
            "item_id": db_item.id,
            "quantity": entry['quantity'],
            "offer_type": OfferType(entry['offer_type']),
            "currency": CurrencyType(entry['currency']),
            "price_for_one": entry['price_for_one'],
            "message_id": message_id
        }

        offer_data['id'] = await insert_offer_data_and_return_id(offer_data)
        if not offer_data['id']:
            logger.error(f"Offer insert failed for {offer_data['item_name']}")
            continue

        logger.info(f"Offer inserted successfully for '{offer_data['item_name']}'")
        await arbitrage_finder(offer_data)


# =====================================================
# Main application workflow
# =====================================================
async def trade_group_message_handler():
    logger.info("Database reset & initialization started")

    await clear_messages()
    await drop_messages_table_raw()
    await drop_arbitrage()
    await drop_offers()
    await init_db()

    logger.info("Database initialized successfully")

    offer_message_queue = asyncio.Queue()

    # Launch concurrent async tasks
    client_run_task = asyncio.create_task(run_client_forever())
    listener_task = asyncio.create_task(trade_group_listener(offer_message_queue))
    notification_bot_task = asyncio.create_task(bot_execution())

    logger.info("All async tasks launched (client, listener, bot)")

    await message_handler(offer_message_queue)


# =====================================================
# Entrypoint
# =====================================================
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
