"""High-level card catalog collection workflow."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import requests

from .config import CARDS_INDEX_URL, REQUEST_DELAY
from .fetch import FetchError
from .models import CardSchema, CardValidationError, validate_card
from .parse import parse_card_page
from .results import CollectionFailure, CollectionResult
from .sets import parse_card_urls, parse_sets

Logger = Callable[[str], None]


class CollectionError(RuntimeError):
    """A collection cannot proceed because its persisted state is invalid."""


class CardSource(Protocol):
    def list_sets(self) -> list[dict[str, Any]]: ...

    def list_card_urls(self, set_id: str) -> list[str]: ...

    def get_card_page(self, url: str) -> str: ...


@dataclass(frozen=True, slots=True)
class CardCollectionOptions:
    test_mode: bool = False
    only_set: str | None = None
    resume: bool = True
    save_every: int = 50


@dataclass(frozen=True, slots=True)
class CardCollectionSummary:
    cards: list[CardSchema]


@dataclass(slots=True)
class InMemoryCardSource:
    sets: list[dict[str, Any]]
    card_urls: dict[str, list[str]]
    card_pages: dict[str, str | Exception]

    def list_sets(self) -> list[dict[str, Any]]:
        return self.sets

    def list_card_urls(self, set_id: str) -> list[str]:
        return self.card_urls[set_id]

    def get_card_page(self, url: str) -> str:
        page = self.card_pages[url]
        if isinstance(page, Exception):
            raise page
        return page


class HttpCardSource:
    """Limitless card source with transport and rate limiting kept local."""

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        delay: float = REQUEST_DELAY,
    ) -> None:
        self._owns_session = session is None
        self._session = session or requests.Session()
        self._delay = delay

    def list_sets(self) -> list[dict[str, Any]]:
        from .fetch import fetch_html

        return parse_sets(fetch_html(CARDS_INDEX_URL, session=self._session))

    def list_card_urls(self, set_id: str) -> list[str]:
        from .fetch import fetch_html

        html = fetch_html(f"{CARDS_INDEX_URL}/{set_id}", session=self._session)
        return parse_card_urls(html, set_id)

    def get_card_page(self, url: str) -> str:
        from .fetch import fetch_html

        html = fetch_html(url, session=self._session)
        if self._delay:
            time.sleep(self._delay)
        return html

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> HttpCardSource:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_checkpoint(path: Path) -> dict[str, CardSchema]:
    if not path.exists():
        return {}
    try:
        cards = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cards, list):
            raise TypeError("checkpoint root must be a list")
        parsed_cards = [CardSchema.from_dict(card) for card in cards]
        return {card.url: card for card in parsed_cards}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise CollectionError(f"malformed checkpoint {path}: {exc}") from exc


def collect_card_catalog(
    options: CardCollectionOptions,
    source: CardSource,
    output_directory: Path,
    *,
    log: Logger = print,
) -> CollectionResult[CardCollectionSummary]:
    output_path = output_directory / "cards.json"
    checkpoint_path = output_directory / "cards.checkpoint.json"
    failure_path = output_directory / "failed_urls.json"
    collected = _load_checkpoint(checkpoint_path) if options.resume else {}

    sets = source.list_sets()
    if options.only_set:
        sets = [item for item in sets if item["set_id"] == options.only_set]
    elif options.test_mode:
        sets = sets[:2]

    failures: list[CollectionFailure] = []
    collected_count = 0
    skipped_count = 0
    processed_since_save = 0
    for set_info in sets:
        set_id = set_info["set_id"]
        try:
            urls = source.list_card_urls(set_id)
        except FetchError as exc:
            failures.append(CollectionFailure(f"{set_id} (set page)", str(exc)))
            continue
        for url in urls:
            if url in collected:
                skipped_count += 1
                continue
            try:
                card = parse_card_page(source.get_card_page(url), url)
                validate_card(card)
            except (FetchError, CardValidationError) as exc:
                failures.append(CollectionFailure(url, str(exc)))
                continue
            collected[url] = card
            collected_count += 1
            processed_since_save += 1
            if processed_since_save >= options.save_every:
                _write_json(
                    checkpoint_path,
                    [card.to_dict() for card in collected.values()],
                )
                processed_since_save = 0

    cards = list(collected.values())
    artifact_cards = [card.to_dict() for card in cards]
    _write_json(checkpoint_path, artifact_cards)
    _write_json(output_path, artifact_cards)
    _write_json(failure_path, [failure.item_id for failure in failures])
    log(f"done: {len(cards)} cards, {len(failures)} failure(s) -> {output_path}")
    return CollectionResult(
        collected_count=collected_count,
        skipped_count=skipped_count,
        failures=failures,
        artifacts={
            "catalog": output_path,
            "checkpoint": checkpoint_path,
            "failures": failure_path,
        },
        summary=CardCollectionSummary(cards=cards),
    )
