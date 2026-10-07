from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Priority(str, PyEnum):
    low = "low"
    medium = "medium"
    high = "high"


class Marketplace(str, PyEnum):
    wb = "wb"
    ozon = "ozon"
    yandex = "yandex"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority, name="priority_level"),
        default=Priority.medium,
        nullable=False,
    )
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="item", cascade="all, delete-orphan",
    )


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("item_id", "url"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    marketplace: Mapped[Marketplace] = mapped_column(
        SAEnum(Marketplace, name="marketplace_type"), nullable=False,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    item: Mapped[Item] = relationship(back_populates="offers")
    history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan",
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("offers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    offer: Mapped[Offer] = relationship(back_populates="history")
