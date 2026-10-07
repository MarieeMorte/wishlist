from decimal import Decimal

from pydantic import BaseModel

from app.models import Marketplace, Priority


class OfferCreate(BaseModel):
    url: str
    marketplace: Marketplace
    price: Decimal | None = None


class ItemCreate(BaseModel):
    title: str
    note: str | None = None
    priority: Priority = Priority.medium
    target_price: Decimal | None = None
    offers: list[OfferCreate] = []


class ItemPatch(BaseModel):
    title: str | None = None
    note: str | None = None
    priority: Priority | None = None
    target_price: Decimal | None = None


class PriceUpdate(BaseModel):
    price: Decimal
