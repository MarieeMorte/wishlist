from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401 — регистрирует модели в Base
from app.db import Base, engine
from app.routers import items

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wishlist")
app.include_router(items.router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}