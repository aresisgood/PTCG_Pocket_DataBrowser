"""External API request and response contracts."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_text(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class CardInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    set: str = Field(min_length=1, max_length=20)
    number: str = Field(min_length=1, max_length=20)
    name: str | None = Field(default=None, max_length=200)
    count: int = Field(default=1, ge=1, le=2, strict=True)

    @field_validator("set", "number", "name", mode="before")
    @classmethod
    def strip_text_fields(cls, value: object) -> object:
        return _strip_text(value)


class DeckWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    cards: list[CardInput] = Field(default_factory=list)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return _strip_text(value)


class DeckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    # Existing SQLite rows predate strict write validation.  Keep their JSON
    # payload intact on reads so a legacy deck remains viewable and editable.
    cards: list[dict[str, Any]]
    created_at: datetime


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cards: list[CardInput] = Field(min_length=1)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
