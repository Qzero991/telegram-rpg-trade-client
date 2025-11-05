from sqlalchemy.orm import selectinload

from database.db_main import engine, Base, session_factory
from database.models import Items, ItemType, Offers, OfferType, Messages, CurrencyType, Arbitrage
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy import select, delete, update, text, and_
from datetime import timezone
import hashlib


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def clear_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def clear_messages():
    async with session_factory() as session:
        await session.execute(delete(Messages))
        await session.commit()

async def drop_messages_table_raw():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("""DELETE FROM messages ;"""))
            await conn.execute(text("""DROP TABLE IF EXISTS messages CASCADE;"""))
            await conn.commit()
        except ProgrammingError:
            print("ТАБЛИЦА НЕ СУЩЕСТВУЕТ")

async def clear_offers():
    async with session_factory() as session:
        await session.execute(delete(Offers))
        await session.commit()

async def drop_offers():
    async with engine.begin() as conn:
        await conn.execute(text("""DROP TABLE IF EXISTS offers CASCADE;"""))
        await conn.commit()


async def drop_arbitrage():
    async with engine.begin() as conn:
        await conn.execute(text("""DROP TABLE IF EXISTS arbitrage CASCADE;"""))
        await conn.commit()


async def insert_item_data(data):
    async with session_factory() as session:
        new_item = Items(
            in_game_id=data["in_game_id"],
            item_name=data["item_name"],
            item_type=ItemType(data["item_type"]),
            item_grade=data["item_grade"],
            item_duration=data["item_duration"]
        )

        try:
            session.add(new_item)
            await session.commit()
        except IntegrityError:
            await session.rollback()  # обязательно откатываем транзакцию
            print("Произошла ошибка целостности данных (например, дубликат ключа)")



async def insert_offer_data_and_return_id(offer_data_dict):
    async with session_factory() as session:
        new_offer = Offers(
            item_name_message=offer_data_dict['item_name_message'],
            item_name_db= offer_data_dict['item_name_db'],
            item_id=offer_data_dict['item_id'],
            quantity=offer_data_dict['quantity'],
            offer_type=offer_data_dict['offer_type'],
            currency=offer_data_dict['currency'],
            price_for_one=offer_data_dict['price_for_one'],
            message_id=offer_data_dict['message_id'],
        )
        try:
            session.add(new_offer)
            await session.flush()
            offer_id = new_offer.id
            await session.commit()
            return offer_id
        except IntegrityError:
            await session.rollback()  # обязательно откатываем транзакцию
            print("Произошла ошибка целостности данных (например, дубликат ключа)")
            return None

async def insert_message_data_and_return_id(event_obj):
    async with session_factory() as session:
        sender = await event_obj.get_sender()
        new_message = Messages(
            message_group_id=event_obj.message.id,
            sender_username=sender.username,
            sender_id=event_obj.sender_id,
            message_text=event_obj.raw_text,
            message_text_hashed=hash_message(event_obj.raw_text),
            sent_at=event_obj.date
        )
        try:
            session.add(new_message)
            await session.flush()
            mes_id = new_message.id
            await session.commit()
            return mes_id
        except IntegrityError:
            await session.rollback()  # обязательно откатываем транзакцию
            print("Произошла ошибка целостности данных (например, дубликат ключа)")
            return None





async def get_items():
    async with session_factory() as session:
        query = select(Items).order_by(Items.id)
        result = await session.execute(query)
        return result.scalars().all()



async def get_filtered_offers(offer_data_dict):
    query_for_buy = (
        select(
            Offers
        )
        .filter(and_(
            Offers.item_id == offer_data_dict['item_id'],
            Offers.currency == offer_data_dict['currency'],
            Offers.price_for_one < offer_data_dict['price_for_one'],
            Offers.offer_type == OfferType.SELL
        ))
    )

    query_for_sell = (
        select(
            Offers
        )
        .filter(and_(
            Offers.item_id == offer_data_dict['item_id'],
            Offers.currency == offer_data_dict['currency'],
            Offers.price_for_one > offer_data_dict['price_for_one'],
            Offers.offer_type == OfferType.BUY
        ))
    )

    if offer_data_dict['offer_type'] == OfferType.SELL:
        query = query_for_sell
    else:
        query = query_for_buy

    async with session_factory() as session:
        result = await session.execute(query)
        return result.scalars().all()



async def insert_arbitrage_data(buy_offer, sell_offer):
    profit_for_one = buy_offer['price_for_one'] - sell_offer['price_for_one']

    if sell_offer['quantity'] and buy_offer['quantity']:
        quantity = min(sell_offer['quantity'], buy_offer['quantity'])
        profit_for_all = quantity * profit_for_one
        price_for_all = quantity * sell_offer['price_for_one']
    else:
        quantity = None
        profit_for_all = None
        price_for_all = None

    async with session_factory() as session:
        new_arbitrage = Arbitrage(
            item_name=buy_offer['item_name'],
            buy_offer=buy_offer['id'],
            sell_offer=sell_offer['id'],
            currency=sell_offer['currency'],
            profit_for_one=profit_for_one,
            profit_for_all=profit_for_all,
            price_for_one=sell_offer['price_for_one'],
            price_for_all=price_for_all,
            quantity=quantity
        )
        try:
            session.add(new_arbitrage)
            await session.flush()
            new_arbitrage_id = new_arbitrage.id
            await session.commit()
            # await get_arbitrage_message_item_data_for_bot(new_arbitrage_id)
            return new_arbitrage_id

        except IntegrityError:
            await session.rollback()  # обязательно откатываем транзакцию
            print("Произошла ошибка целостности данных (например, дубликат ключа)")


async def get_arbitrage_message_item_data_for_bot(arbitrage_id):

    query = (
        select(
            Arbitrage
        )
        .options(
            selectinload(Arbitrage.buy_offer_rel)
            .selectinload(Offers.item),
            selectinload(Arbitrage.buy_offer_rel)
            .selectinload(Offers.message),

            selectinload(Arbitrage.sell_offer_rel)
            .selectinload(Offers.item),
            selectinload(Arbitrage.sell_offer_rel)
            .selectinload(Offers.message)
        )
        .filter(Arbitrage.id == arbitrage_id)
    )

    async with session_factory() as session:
        result = await session.execute(query)
        result = result.scalars().all()
    return result[0]




async def delete_offer_by_id(offer_id):
    async with session_factory() as session:
        query = (
            delete(
                Offers
            )
            .where(
                Offers.id == offer_id
            )
        )
        await session.execute(query)
        await session.commit()

async def update_quantity_in_offer_by_id(offer_id, new_quantity):
    async with session_factory() as session:
        query = (
            update(
                Offers
            )
            .where(
                Offers.id == offer_id
            )
            .values(
                quantity= new_quantity
            )
        )
        await session.execute(query)
        await session.commit()


def hash_message(text):
    # убираем пробелы по краям и переводим в нижний регистр (чтобы хэш был устойчивее)
    normalized = text.strip().lower().encode('utf-8')
    return hashlib.sha256(normalized).hexdigest()
