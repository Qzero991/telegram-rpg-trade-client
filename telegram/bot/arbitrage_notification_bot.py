import requests
from config import settings

text = """
🚨🚨🚨  ARBITRAGE FOUND!  🚨🚨🚨

📦 ITEM INFO
━━━━━━━━━━━━━━━━━━━━━━━
🪙 Name: {item_name}
🏷️ Type: {item_type}
⭐ Grade: {item_grade}
⌛ Duration: {item_duration}

💰 ARBITRAGE DATA
━━━━━━━━━━━━━━━━━━━━━━━
💵 Currency: {currency}
📈 Profit (per one): {profit_for_one}
💹 Profit (total): {profit_for_all}
💰 Total price: {price_for_all}

📤 SELL OFFER
━━━━━━━━━━━━━━━━━━━━━━━
🔗 Message: {link_to_the_sell_message}
👤 Seller: {link_to_the_sell_sender}
💵 Price (per one): {sell_price}
📦 Quantity: {sell_quantity}

📥 BUY OFFER
━━━━━━━━━━━━━━━━━━━━━━━
🔗 Message: {link_to_the_buy_message}
👤 Buyer: {link_to_the_buy_sender}
💵 Price (per one): {buy_price}
📦 Quantity: {buy_quantity}

━━━━━━━━━━━━━━━━━━━━━━━
"""


async def send_telegram_message(query_result):
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    item = query_result.buy_offer_rel.item
    sell_offer = query_result.sell_offer_rel
    buy_offer = query_result.buy_offer_rel
    sell_link = f"https://t.me/c/{str(settings.trade_group_id)[4:]}/{sell_offer.message.message_group_id}"
    buy_link = f"https://t.me/c/{str(settings.trade_group_id)[4:]}/{buy_offer.message.message_group_id}"
    sell_sender_link = f"https://t.me/{sell_offer.message.sender_username}"
    buy_sender_link = f"https://t.me/{buy_offer.message.sender_username}"
    data = {
        "chat_id": settings.my_id,
        "text": text.format(
            item_name=item.item_name,
            item_type=item.item_type,
            item_grade=item.item_grade,
            item_duration=item.item_duration,
            currency=query_result.currency,
            profit_for_one=query_result.profit_for_one,
            profit_for_all=query_result.profit_for_all,
            price_for_all=query_result.price_for_all,
            link_to_the_sell_message=sell_link,
            link_to_the_sell_sender=sell_sender_link,
            sell_price=sell_offer.price_for_one,
            sell_quantity=sell_offer.quantity,
            link_to_the_buy_message=buy_link,
            link_to_the_buy_sender=buy_sender_link,
            buy_price=buy_offer.price_for_one,
            buy_quantity=buy_offer.quantity
        )
    }
    response = requests.post(url, data=data)

    # Проверим успешность
    if response.status_code != 200:
        print("Ошибка при отправке:", response.text)
    else:
        print("Сообщение отправлено!")





