import logging
from database.queries import get_filtered_offers, insert_arbitrage_data, get_arbitrage_message_item_data_for_bot
from database.models import OfferType
from telegram.bot.arbitrage_notification_bot import send_telegram_message

logger = logging.getLogger(__name__)


# Finds arbitrage opportunities between offers and saves profitable pairs to the database.
async def arbitrage_finder(offer_data_dict):

    logger.info(f"Starting arbitrage search for item: {offer_data_dict.get('item_name')}")

    # Get all offers suitable for arbitrage comparison
    arbitrage_offers = await get_filtered_offers(offer_data_dict)
    if not arbitrage_offers:
        logger.info("No arbitrage opportunities found.")
        return

    # Define insertion logic depending on offer type
    if offer_data_dict['offer_type'] == OfferType.SELL:
        async def insert(second_offer):
            return await insert_arbitrage_data(buy_offer=second_offer, sell_offer=offer_data_dict)
    else:
        async def insert(second_offer):
            return await insert_arbitrage_data(buy_offer=offer_data_dict, sell_offer=second_offer)

    # Loop through offers and save arbitrage results
    for offer in arbitrage_offers:
        second_offer_data_dict = {
            "id": offer.id,
            "item_name": offer.item_name_db,
            "currency": offer.currency,
            "price_for_one": offer.price_for_one,
            "quantity": offer.quantity
        }

        try:
            arbitrage_id = await insert(second_offer_data_dict)
            result_data = await get_arbitrage_message_item_data_for_bot(arbitrage_id)
            await send_telegram_message(result_data)
            logger.info(
                f"Arbitrage found and saved: {offer_data_dict.get('item_name')} "
                f"(arbitrage_id={arbitrage_id})"
            )
        except Exception as e:
            logger.error(f"Error while processing arbitrage for {offer.item_name_db}: {e}")

    logger.info("Arbitrage search finished.")
