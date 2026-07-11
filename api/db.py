"""SQLite 連線與 session 管理(SQLModel）。

engine 為模組層級變數,測試時以 monkeypatch 換成暫存資料庫即可。
"""
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from scraper.config import DATA_DIR

DB_PATH = DATA_DIR / "decks.db"

# check_same_thread=False:讓 FastAPI 的多執行緒可共用同一連線(SQLite 慣例）。
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """建立所有資料表(若尚未存在）。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 相依:提供一個資料庫 session。"""
    with Session(engine) as session:
        yield session
