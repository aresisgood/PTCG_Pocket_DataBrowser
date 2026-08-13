"""Machine-readable outcomes shared by scraper collection workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CollectionFailure:
    item_id: str
    message: str


@dataclass(slots=True)
class CollectionResult:
    collected_count: int = 0
    skipped_count: int = 0
    failures: list[CollectionFailure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    artifacts: dict[str, Path] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
