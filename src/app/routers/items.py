from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Item, Offer, PriceHistory
from app.schemas import ItemCreate, OfferCreate, PriceUpdate

router = APIRouter(prefix="/api")

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

PRICE_BUCKETS: list[tuple[Decimal | None, Decimal | None, str]] = [
    (None, Decimal("200"), "до 200 ₽"),
    (Decimal("200"), Decimal("500"), "200–500 ₽"),
    (Decimal("500"), Decimal("1000"), "500–1000 ₽"),
    (Decimal("1000"), Decimal("2000"), "1000–2000 ₽"),
    (Decimal("2000"), Decimal("5000"), "2000–5000 ₽"),
    (Decimal("5000"), Decimal("8000"), "5000–8000 ₽"),
    (Decimal("8000"), Decimal("12000"), "8000–12000 ₽"),
    (Decimal("12000"), None, "более 12000 ₽"),
]


def _serialize(item: Item) -> dict:
    prices = [o.last_price for o in item.offers if o.last_price is not None]
    min_price = min(prices) if prices else None
    is_hit = (
            item.target_price is not None
            and min_price is not None
            and min_price <= item.target_price
    )
    return {
        "id": item.id,
        "title": item.title,
        "note": item.note,
        "priority": item.priority.value,
        "target_price": str(item.target_price) if item.target_price is not None else None,
        "min_price": str(min_price) if min_price is not None else None,
        "is_target_hit": is_hit,
        "offers": [
            {
                "id": o.id,
                "url": o.url,
                "marketplace": o.marketplace.value,
                "last_price": str(o.last_price) if o.last_price is not None else None,
            }
            for o in item.offers
        ],
    }


def _bucket_price(value: Decimal | None) -> tuple[str, int]:
    if value is None:
        return "без цены", 999
    for i, (lo, hi, label) in enumerate(PRICE_BUCKETS):
        if (lo is None or value >= lo) and (hi is None or value < hi):
            return label, i
    return "без цены", 999


def _group(items: list[dict], group_by: str) -> list[dict]:
    if group_by == "priority":
        labels = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}
        order = ["high", "medium", "low"]
        buckets: dict[str, list] = {k: [] for k in order}
        for it in items:
            buckets[it["priority"]].append(it)
        return [
            {"key": k, "label": labels[k], "items": buckets[k]}
            for k in order if buckets[k]
        ]

    if group_by == "price":
        buckets: dict[str, tuple[int, list]] = {}
        for it in items:
            value = Decimal(it["min_price"]) if it["min_price"] else None
            label, idx = _bucket_price(value)
            buckets.setdefault(label, (idx, []))[1].append(it)
        ordered = sorted(buckets.items(), key=lambda kv: kv[1][0])
        return [{"key": k, "label": k, "items": v[1]} for k, v in ordered]

    # created
    buckets: dict[str, list] = {}
    for it in items:
        label = "Пора брать" if it["is_target_hit"] else "Ранее"
        buckets.setdefault(label, []).append(it)
    preferred = ["Пора брать", "Ранее"]
    return [
        {"key": k, "label": k, "items": buckets[k]}
        for k in preferred if k in buckets
    ]


def _sort_key(sort: str):
    if sort == "price_desc":
        return lambda it: Decimal(it["min_price"]) if it["min_price"] else Decimal("1e12"), True
    if sort == "priority":
        return lambda it: PRIORITY_ORDER.get(it["priority"], 99), False
    if sort == "created_desc":
        return lambda it: -it["id"], False
    return lambda it: Decimal(it["min_price"]) if it["min_price"] else Decimal("1e12"), False


def _summary(items: list[dict]) -> dict:
    total = sum(
        (Decimal(i["min_price"]) for i in items if i["min_price"]), Decimal(0),
    )
    return {
        "total_items": len(items),
        "total_min_price": str(total),
        "target_hits": sum(1 for i in items if i["is_target_hit"]),
    }


@router.get("/items")
def list_items(
        group_by: str = "price",
        sort: str = "price_asc",
        priority: str = "",
        price_min: Decimal | None = None,
        price_max: Decimal | None = None,
        target_hit: bool | None = None,
        q: str = "",
        db: Session = Depends(get_db),
):
    items = db.query(Item).all()
    serialized = [_serialize(i) for i in items]

    if priority:
        wanted = set(p.strip() for p in priority.split(","))
        serialized = [i for i in serialized if i["priority"] in wanted]

    if price_min is not None:
        serialized = [
            i for i in serialized
            if i["min_price"] is not None and Decimal(i["min_price"]) >= price_min
        ]
    if price_max is not None:
        serialized = [
            i for i in serialized
            if i["min_price"] is not None and Decimal(i["min_price"]) <= price_max
        ]
    if target_hit is not None:
        serialized = [i for i in serialized if i["is_target_hit"] == target_hit]
    if q:
        needle = q.lower()
        serialized = [
            i for i in serialized
            if needle in (i["title"] or "").lower()
               or needle in (i["note"] or "").lower()
        ]

    key, reverse = _sort_key(sort)
    serialized.sort(key=key, reverse=reverse)

    return {
        "groups": _group(serialized, group_by),
        "summary": _summary(serialized),
    }


@router.post("/items", status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = Item(
        title=payload.title,
        note=payload.note,
        priority=payload.priority,
        target_price=payload.target_price,
    )
    db.add(item)
    db.flush()

    for offer_in in payload.offers:
        offer = Offer(
            item_id=item.id,
            url=offer_in.url,
            marketplace=offer_in.marketplace,
            last_price=offer_in.price,
        )
        db.add(offer)
        db.flush()
        if offer_in.price is not None:
            db.add(PriceHistory(offer_id=offer.id, price=offer_in.price))

    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.patch("/offers/{offer_id}/price")
def set_offer_price(offer_id: int, payload: PriceUpdate, db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(404, "оффер не найден")
    offer.last_price = payload.price
    db.add(PriceHistory(offer_id=offer.id, price=payload.price))
    db.commit()
    db.refresh(offer)
    return {
        "id": offer.id,
        "last_price": str(offer.last_price),
        "item_id": offer.item_id,
    }
