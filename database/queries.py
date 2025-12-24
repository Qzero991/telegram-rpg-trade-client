import logging
import hashlib

from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy import select, delete, update, text, and_

from database.db_main import engine, Base, session_factory
from database.models import Items, ItemType, Offers, OfferType, Messages, Arbitrage

logger = logging.getLogger(__name__)


# Database initialization
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized.")


# Drop all tables
async def clear_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database cleared (all tables dropped).")

async def clear_db_without_items():
    await drop_messages_table_raw()
    await drop_offers()
    await drop_arbitrage()

# Message operations
async def clear_messages():
    async with session_factory() as session:
        await session.execute(delete(Messages))
        await session.commit()
        logger.info("All messages cleared.")


async def drop_messages_table_raw():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("""DELETE FROM messages;"""))
            await conn.execute(text("""DROP TABLE IF EXISTS messages CASCADE;"""))
            await conn.commit()
            logger.info("Messages table dropped.")
        except ProgrammingError:
            logger.warning("Messages table does not exist.")


# Offer operations
async def clear_offers():
    async with session_factory() as session:
        await session.execute(delete(Offers))
        await session.commit()
        logger.info("All offers cleared.")


async def drop_offers():
    async with engine.begin() as conn:
        await conn.execute(text("""DROP TABLE IF EXISTS offers CASCADE;"""))
        await conn.commit()
        logger.info("Offers table dropped.")


async def drop_arbitrage():
    async with engine.begin() as conn:
        await conn.execute(text("""DROP TABLE IF EXISTS arbitrage CASCADE;"""))
        await conn.commit()
        logger.info("Arbitrage table dropped.")


# Insert data
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
            logger.info(f"Inserted item: {new_item.item_name}")
        except IntegrityError:
            await session.rollback()
            logger.warning("Integrity error while inserting item (duplicate or invalid key).")


async def insert_offer_data_and_return_id(offer_data_dict):
    async with session_factory() as session:
        new_offer = Offers(
            item_name_message=offer_data_dict['item_name_message'],
            item_name_db=offer_data_dict['item_name_db'],
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
            logger.info(f"Inserted offer with id={offer_id}")
            return offer_id
        except IntegrityError:
            await session.rollback()
            logger.warning("Integrity error while inserting offer.")
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
            logger.info(f"Inserted message with id={mes_id}")
            return mes_id
        except IntegrityError:
            await session.rollback()
            logger.warning("Integrity error while inserting message.")
            return None


# Select operations
async def get_items():
    async with session_factory() as session:
        query = select(Items).order_by(Items.id)
        result = await session.execute(query)
        logger.debug("Fetched all items from DB.")
        return result.scalars().all()

# Select opposite-type offers to detect arbitrage opportunities.
async def get_filtered_offers(offer_data_dict):
    query_for_buy = (
        select(Offers)
        .filter(and_(
            Offers.item_id == offer_data_dict['item_id'],
            Offers.currency == offer_data_dict['currency'],
            Offers.price_for_one < offer_data_dict['price_for_one'],
            Offers.offer_type == OfferType.SELL
        ))
    )

    query_for_sell = (
        select(Offers)
        .filter(and_(
            Offers.item_id == offer_data_dict['item_id'],
            Offers.currency == offer_data_dict['currency'],
            Offers.price_for_one > offer_data_dict['price_for_one'],
            Offers.offer_type == OfferType.BUY
        ))
    )

    query = query_for_sell if offer_data_dict['offer_type'] == OfferType.SELL else query_for_buy

    async with session_factory() as session:
        result = await session.execute(query)
        logger.debug("Fetched filtered offers for arbitrage check.")
        return result.scalars().all()

# Insert new arbitrage record based on two offers.
async def insert_arbitrage_data(buy_offer, sell_offer):
    profit_for_one = buy_offer['price_for_one'] - sell_offer['price_for_one']

    if sell_offer['quantity'] and buy_offer['quantity']:
        quantity = min(sell_offer['quantity'], buy_offer['quantity'])
        profit_for_all = quantity * profit_for_one
        price_for_all = quantity * sell_offer['price_for_one']
    else:
        quantity = profit_for_all = price_for_all = None

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
            new_id = new_arbitrage.id
            await session.commit()
            logger.info(f"Inserted arbitrage with id={new_id}")
            return new_id
        except IntegrityError:
            await session.rollback()
            logger.warning("Integrity error while inserting arbitrage.")


# Fetch arbitrage data with related offers, items and messages.
async def get_arbitrage_message_item_data_for_bot(arbitrage_id):
    query = (
        select(Arbitrage)
        .options(
            selectinload(Arbitrage.buy_offer_rel).selectinload(Offers.item),
            selectinload(Arbitrage.buy_offer_rel).selectinload(Offers.message),
            selectinload(Arbitrage.sell_offer_rel).selectinload(Offers.item),
            selectinload(Arbitrage.sell_offer_rel).selectinload(Offers.message)
        )
        .filter(Arbitrage.id == arbitrage_id)
    )

    async with session_factory() as session:
        result = await session.execute(query)
        logger.debug(f"Fetched arbitrage data for id={arbitrage_id}")
        result = result.scalars().all()
    return result[0]


# Update / Delete
async def delete_offer_by_id(offer_id):
    async with session_factory() as session:
        query = delete(Offers).where(Offers.id == offer_id)
        await session.execute(query)
        await session.commit()
        logger.info(f"Deleted offer id={offer_id}")


async def update_quantity_in_offer_by_id(offer_id, new_quantity):
    async with session_factory() as session:
        query = (
            update(Offers)
            .where(Offers.id == offer_id)
            .values(quantity=new_quantity)
        )
        await session.execute(query)
        await session.commit()
        logger.info(f"Updated quantity for offer id={offer_id} to {new_quantity}")


# Normalize message text and return SHA-256 hash.
def hash_message(text: str) -> str:
    normalized = text.strip().lower().encode('utf-8')
    return hashlib.sha256(normalized).hexdigest()
