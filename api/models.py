"""API 資料模型:SQLite 牌組資料表 + 請求/回應 schema。

牌組的卡片清單以 JSON 欄位存放(單人本機使用,結構簡單即可)。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Deck(SQLModel, table=True):
    """存於 SQLite 的牌組。"""
    id: int | None = Field(default=None, primary_key=True)
    name: str
    cards: list[dict[str, Any]] = Field(default_factory=list,
                                        sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
