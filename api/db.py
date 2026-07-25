"""Database URL, engine, schema, and request-session management."""
from __future__ import annotations

import os
from typing import Any

from fastapi import Request
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, SQLModel, create_engine

from scraper.config import DATA_DIR

DB_PATH = DATA_DIR / "decks.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def engine_options(database_url: str) -> dict[str, Any]:
    if make_url(database_url).get_backend_name() == "sqlite":
        return {"connect_args": {"check_same_thread": False}}
    return {}


def create_db_engine(database_url: str) -> Engine:
    return create_engine(database_url, **engine_options(database_url))


def init_db(engine: Engine) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session(request: Request):
    with Session(request.app.state.db_engine) as session:
        yield session
