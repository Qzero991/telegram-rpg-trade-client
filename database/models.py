from tkinter.constants import CASCADE
from datetime import datetime, timezone
import enum
from sqlalchemy import Integer, String, UniqueConstraint, Enum, ForeignKey, nulls_last, text, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.db_main import Base


class ItemType(enum.Enum):
    EQUIPMENT = "equipment"
    RESOURCE = "resource"

class OfferType(enum.Enum):
    SELL = "sell"
    BUY = "buy"
    TRADE = "trade"

class CurrencyType(enum.Enum):
    COOKIES = "cookies"
    MONEY = "money"


class Items(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    in_game_id: Mapped[int] = mapped_column(Integer, nullable=False)
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)
    item_grade: Mapped[str] = mapped_column(String(10), nullable=False)
    item_duration: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        UniqueConstraint("item_name", "item_grade", "item_duration", name="_name_grade_duration_uc"),
    )

    offers: Mapped[list["Offers"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan"
    )

class Messages(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_text: Mapped[str] = mapped_column(String, nullable=False)
    message_text_hashed: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),  default=lambda: datetime.now(timezone.utc))

    offers: Mapped[list["Offers"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan"
    )


class Offers(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_name_message: Mapped[str] = mapped_column(String, nullable=False)
    item_name_db: Mapped[str] = mapped_column(String, nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey(Items.id, ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=True)
    offer_type: Mapped[OfferType] = mapped_column(Enum(OfferType), nullable=False)
    currency: Mapped[CurrencyType] = mapped_column(Enum(CurrencyType), nullable=False)
    price_for_one: Mapped[int] = mapped_column(Integer, nullable=False)
    message_id: Mapped[int] = mapped_column(ForeignKey(Messages.id, ondelete="CASCADE"))


    # связь обратно к Items
    item: Mapped["Items"] = relationship(back_populates="offers")

    # связь обратно к Messages
    message: Mapped["Messages"] = relationship(back_populates="offers")

    # Отдельные relationship для арбитража как покупки и продажи
    arbitrage_as_buy: Mapped[list["Arbitrage"]] = relationship(
        "Arbitrage",
        foreign_keys="Arbitrage.buy_offer",
        back_populates="buy_offer_rel",
        cascade="all, delete-orphan"
    )
    arbitrage_as_sell: Mapped[list["Arbitrage"]] = relationship(
        "Arbitrage",
        foreign_keys="Arbitrage.sell_offer",
        back_populates="sell_offer_rel",
        cascade="all, delete-orphan"
    )

class Arbitrage(Base):
    __tablename__ = "arbitrage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    buy_offer: Mapped[int] = mapped_column(ForeignKey(Offers.id, ondelete="CASCADE"))
    sell_offer: Mapped[int] = mapped_column(ForeignKey(Offers.id, ondelete="CASCADE"))
    currency: Mapped[CurrencyType] = mapped_column(Enum(CurrencyType), nullable=False)
    profit_for_one: Mapped[int] = mapped_column(Integer, nullable=False)
    profit_for_all: Mapped[int] = mapped_column(Integer, nullable=True)
    price_for_one: Mapped[int] = mapped_column(Integer, nullable=False)
    price_for_all: Mapped[int] = mapped_column(Integer, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relationship для предложения покупки
    buy_offer_rel: Mapped["Offers"] = relationship(
        "Offers",
        foreign_keys=[buy_offer],
        back_populates="arbitrage_as_buy"
    )

    # Relationship для предложения продажи
    sell_offer_rel: Mapped["Offers"] = relationship(
        "Offers",
        foreign_keys=[sell_offer],
        back_populates="arbitrage_as_sell"
    )








