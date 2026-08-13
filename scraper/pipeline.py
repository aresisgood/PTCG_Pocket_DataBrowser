"""Backward-compatible adapter for the card catalog collection workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from project_config import DATA_DIR

from .card_catalog import (
    CardCollectionOptions,
    CardSource,
    HttpCardSource,
    collect_card_catalog,
)

Logger = Callable[[str], None]


def scrape(
    *,
    test_mode: bool = False,
    only_set: str | None = None,
    resume: bool = True,
    log: Logger = print,
    source: CardSource | None = None,
    output_directory: Path = DATA_DIR,
) -> list[dict[str, Any]]:
    """Run card collection while preserving the historical return value."""
    options = CardCollectionOptions(
        test_mode=test_mode, only_set=only_set, resume=resume
    )
    if source is not None:
        result = collect_card_catalog(options, source, output_directory, log=log)
    else:
        with HttpCardSource() as http_source:
            result = collect_card_catalog(
                options, http_source, output_directory, log=log
            )
    return result.summary["cards"]
