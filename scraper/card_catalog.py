"""High-level card catalog collection workflow."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
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

CATALOG_FILENAME = "cards.json"
CHECKPOINT_FILENAME = "cards.checkpoint.json"
FRESH_PROGRESS_FILENAME = "cards.fresh.checkpoint.json"
FAILURE_FILENAME = "failed_urls.json"


class CollectionError(RuntimeError):
    """A collection cannot proceed because its persisted state is invalid."""


class CollectionInterrupted(KeyboardInterrupt):
    """The operator stopped collection; whatever was collected is persisted.

    This stays a ``KeyboardInterrupt`` so that an ``except Exception`` added
    around the workflow later cannot silently swallow an operator's Ctrl+C.
    """

    def __init__(
        self,
        collected_count: int,
        progress_path: Path | None = None,
        failure_count: int = 0,
    ) -> None:
        location = (
            f"progress saved to {progress_path}"
            if progress_path is not None
            else "no progress to save"
        )
        super().__init__(
            f"collection interrupted after {collected_count} new card(s) and "
            f"{failure_count} failure(s); {location}"
        )
        self.collected_count = collected_count
        self.progress_path = progress_path
        self.failure_count = failure_count


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
    card_pages: dict[str, str | BaseException]

    def list_sets(self) -> list[dict[str, Any]]:
        return self.sets

    def list_card_urls(self, set_id: str) -> list[str]:
        return self.card_urls[set_id]

    def get_card_page(self, url: str) -> str:
        page = self.card_pages[url]
        if isinstance(page, BaseException):
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
    """Replace ``path`` atomically, so an interrupt cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f"{path.name}.tmp")
    staging.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(staging, path)


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


@dataclass(frozen=True, slots=True)
class _CatalogPaths:
    """Where one collection run reads and writes its artifacts."""

    catalog: Path
    checkpoint: Path
    failures: Path
    staging: Path

    @classmethod
    def under(cls, directory: Path) -> "_CatalogPaths":
        return cls(
            catalog=directory / CATALOG_FILENAME,
            checkpoint=directory / CHECKPOINT_FILENAME,
            failures=directory / FAILURE_FILENAME,
            staging=directory / FRESH_PROGRESS_FILENAME,
        )


@dataclass(slots=True)
class _CollectionProgress:
    """Accumulated state of a single collection run."""

    collected: dict[str, CardSchema]
    failures: list[CollectionFailure] = field(default_factory=list)
    collected_count: int = 0
    skipped_count: int = 0

    def as_artifact(self) -> list[dict[str, Any]]:
        return [card.to_dict() for card in self.collected.values()]


def _select_sets(
    sets: list[dict[str, Any]], options: CardCollectionOptions
) -> list[dict[str, Any]]:
    if options.only_set:
        return [item for item in sets if item["set_id"] == options.only_set]
    if options.test_mode:
        return sets[:2]
    return sets


def _gather_cards(
    options: CardCollectionOptions,
    source: CardSource,
    sets: list[dict[str, Any]],
    progress: _CollectionProgress,
    save: Callable[[], Path],
) -> None:
    processed_since_save = 0
    for set_info in sets:
        set_id = set_info["set_id"]
        try:
            urls = source.list_card_urls(set_id)
        except FetchError as exc:
            progress.failures.append(
                CollectionFailure(f"{set_id} (set page)", str(exc))
            )
            continue
        for url in urls:
            if url in progress.collected:
                progress.skipped_count += 1
                continue
            try:
                card = parse_card_page(source.get_card_page(url), url)
                validate_card(card)
            except (FetchError, CardValidationError) as exc:
                progress.failures.append(CollectionFailure(url, str(exc)))
                continue
            progress.collected[url] = card
            progress.collected_count += 1
            processed_since_save += 1
            if processed_since_save >= options.save_every:
                save()
                processed_since_save = 0


def _catalog_size(path: Path) -> int:
    """Count the cards already published, treating anything unreadable as none."""
    if not path.exists():
        return 0
    try:
        published = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    return len(published) if isinstance(published, list) else 0


def _publish_catalog(
    progress: _CollectionProgress,
    paths: _CatalogPaths,
    log: Logger,
) -> CollectionResult[CardCollectionSummary]:
    artifact_cards = progress.as_artifact()
    published_count = _catalog_size(paths.catalog)
    # A scoped re-scrape (--set/--test) or a run where every fetch failed would
    # otherwise publish a handful of cards over the full catalog. Refuse instead,
    # and keep the work staged so nothing has to be fetched twice.
    if len(artifact_cards) < published_count:
        _write_json(paths.staging, artifact_cards)
        raise CollectionError(
            f"refusing to shrink {paths.catalog} from {published_count} to "
            f"{len(artifact_cards)} card(s); the collected cards are staged in "
            f"{paths.staging}. Re-run without --set/--test, or back up and "
            "remove the catalog if the smaller result is intended."
        )

    _write_json(paths.checkpoint, artifact_cards)
    _write_json(paths.catalog, artifact_cards)
    _write_json(paths.failures, [failure.item_id for failure in progress.failures])
    paths.staging.unlink(missing_ok=True)
    log(
        f"done: {len(artifact_cards)} cards, {len(progress.failures)} failure(s) "
        f"-> {paths.catalog}"
    )
    return CollectionResult(
        collected_count=progress.collected_count,
        skipped_count=progress.skipped_count,
        failures=progress.failures,
        artifacts={
            "catalog": paths.catalog,
            "checkpoint": paths.checkpoint,
            "failures": paths.failures,
        },
        summary=CardCollectionSummary(cards=list(progress.collected.values())),
    )


def collect_card_catalog(
    options: CardCollectionOptions,
    source: CardSource,
    output_directory: Path,
    *,
    log: Logger = print,
) -> CollectionResult[CardCollectionSummary]:
    paths = _CatalogPaths.under(output_directory)
    # A fresh run stages progress beside the canonical checkpoint instead of
    # inside it, so an interrupted re-scrape can never replace a complete
    # catalog with the handful of cards it managed to fetch.
    progress_path = paths.checkpoint if options.resume else paths.staging
    progress = _CollectionProgress(
        collected=_load_checkpoint(paths.checkpoint) if options.resume else {}
    )

    def save_progress() -> Path:
        _write_json(progress_path, progress.as_artifact())
        return progress_path

    try:
        _gather_cards(
            options,
            source,
            _select_sets(source.list_sets(), options),
            progress,
            save_progress,
        )
    except KeyboardInterrupt:
        staged = save_progress() if progress.collected else None
        log(
            f"interrupted: {progress.collected_count} new card(s), "
            f"{len(progress.failures)} failure(s); "
            f"{'staged in ' + str(staged) if staged else 'nothing written'}; "
            f"{paths.catalog} left untouched"
        )
        # The operator chose to stop, so the original traceback adds nothing.
        raise CollectionInterrupted(
            progress.collected_count, staged, len(progress.failures)
        ) from None

    return _publish_catalog(progress, paths, log)
