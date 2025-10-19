from database.db_main import engine, Base, session_factory
from database.models import Items, ItemType, Offers, OfferType, Messages, CurrencyType
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy import select, delete, text
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

async def clear_offers():
    async with session_factory() as session:
        await session.execute(delete(Offers))
        await session.commit()

async def drop_offers():
    async with engine.begin() as conn:
        await conn.execute(text("""DROP TABLE IF EXISTS offers CASCADE;"""))
        await conn.commit()

async def drop_messages_table_raw():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("""DELETE FROM messages ;"""))
            await conn.execute(text("""DROP TABLE IF EXISTS messages CASCADE;"""))
            await conn.commit()
        except ProgrammingError:
            print("ТАБЛИЦА НЕ СУЩЕСТВУЕТ")




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

async def insert_offer_data(data_in_dict, item_id_db, message_id_db):
    async with session_factory() as session:
        new_offer = Offers(
            item_name=data_in_dict['item_name'],
            item_id=item_id_db,
            quantity=data_in_dict['quantity'],
            offer_type=OfferType(data_in_dict['offer_type']),
            currency=CurrencyType(data_in_dict['currency']),
            price_for_one=data_in_dict['price_for_one'],
            message_id=message_id_db,
        )
        session.add(new_offer)
        await session.commit()

async def insert_message_data(event_obj):
    async with session_factory() as session:
        new_message = Messages(
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



def hash_message(text):
    # убираем пробелы по краям и переводим в нижний регистр (чтобы хэш был устойчивее)
    normalized = text.strip().lower().encode('utf-8')
    return hashlib.sha256(normalized).hexdigest()
