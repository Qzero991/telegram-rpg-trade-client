import logging

from database.models import OfferType, CurrencyType
from database.queries import insert_offer_data_and_return_id, get_items, insert_message_data_and_return_id
from logic.arbitrage import arbitrage_finder
from logic.matcher import find_top5_item_matches, filter_by_grade_and_duration
from parser.group_message_parser import create_request

logger = logging.getLogger(__name__)


# Message processing: parse, validate, and save to DB
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

        await process_offer(items_in_db, response, message_id)


# Finds match between offer items and db item, then inserts offer in db and calls the arbitrage finder function
async def process_offer(items_in_db, response, message_id):
    for entry in response:
        if not isinstance(entry["price_for_one"], int):
            logger.debug(f"Skipping — invalid price: {entry['price_for_one']}")
            continue

        # Top 5 matches
        top5 = find_top5_item_matches(items_in_db, entry)

        logger.debug(f"Top 5 matches for '{entry['item_name']}': {top5}")

        # Filter
        best_match = filter_by_grade_and_duration(top5, entry, items_in_db)

        if not best_match: continue

        db_item = items_in_db[best_match["index"]]
        logger.info(f"Matched '{entry['item_name']}' → '{db_item.item_name}' ({best_match["score"]:.1f}%)")

        # Prepare and insert offer data
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


