from database.queries import get_filtered_offers
from database.models import OfferType, CurrencyType
from database.queries import insert_arbitrage_data


async def arbitrage_finder(offer_data_dict):

    arbitrage_offers = await get_filtered_offers(offer_data_dict)
    if not arbitrage_offers:
        print("NO ARBITRAGE")
        return

    if offer_data_dict['offer_type'] == OfferType.SELL:
        for buy_offer in arbitrage_offers:
            buy_offer_data_dict = {
                "id": buy_offer.id,
                "item_name": buy_offer.item_name_db,
                "currency": buy_offer.currency,
                "price_for_one": buy_offer.price_for_one,
                "quantity": buy_offer.quantity
            }
            await insert_arbitrage_data(buy_offer=buy_offer_data_dict, sell_offer=offer_data_dict)
    elif offer_data_dict['offer_type'] == OfferType.BUY:
        for sell_offer in arbitrage_offers:
            sell_offer_data_dict = {
                "id": sell_offer.id,
                "item_name": sell_offer.item_name_db,
                "currency": sell_offer.currency,
                "price_for_one": sell_offer.price_for_one,
                "quantity": sell_offer.quantity
            }
            await insert_arbitrage_data(buy_offer=offer_data_dict, sell_offer=sell_offer_data_dict)


