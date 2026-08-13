"""High-level tournament dataset collection workflow."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import requests

from .fetch import FetchError, fetch_json
from .results import CollectionFailure, CollectionResult
from .tournaments import parse_pairings, parse_standings, select_tournaments

Logger = Callable[[str], None]
API_BASE = "https://play.limitlesstcg.com/api"
GAME = "POCKET"
API_DELAY = 1.2


class TournamentSource(Protocol):
    def list_tournaments(self, limit: int) -> list[dict[str, Any]]: ...

    def get_standings(self, tournament_id: str) -> list[dict[str, Any]]: ...

    def get_pairings(self, tournament_id: str) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class TournamentCollectionOptions:
    min_players: int = 50
    after: str | None = None
    max_tournaments: int = 20


@dataclass(frozen=True, slots=True)
class TournamentCollectionSummary:
    selected_tournaments: int
    successful_tournament_ids: list[str]
    failed_tournament_ids: list[str]
    dataset: dict[str, Any]


@dataclass(slots=True)
class InMemoryTournamentSource:
    tournaments: list[dict[str, Any]]
    standings: dict[str, list[dict[str, Any]]]
    pairings: dict[str, list[dict[str, Any]]]

    def list_tournaments(self, limit: int) -> list[dict[str, Any]]:
        return self.tournaments[:limit]

    def get_standings(self, tournament_id: str) -> list[dict[str, Any]]:
        return self.standings[tournament_id]

    def get_pairings(self, tournament_id: str) -> list[dict[str, Any]]:
        return self.pairings[tournament_id]


class HttpTournamentSource:
    """Limitless tournament source with transport and throttling kept local."""

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        delay: float = API_DELAY,
    ) -> None:
        self._owns_session = session is None
        self._session = session or requests.Session()
        self._delay = delay

    def list_tournaments(self, limit: int) -> list[dict[str, Any]]:
        return fetch_json(
            f"{API_BASE}/tournaments",
            params={"game": GAME, "limit": limit},
            session=self._session,
        )

    def get_standings(self, tournament_id: str) -> list[dict[str, Any]]:
        return fetch_json(
            f"{API_BASE}/tournaments/{tournament_id}/standings",
            session=self._session,
        )

    def get_pairings(self, tournament_id: str) -> list[dict[str, Any]]:
        result = fetch_json(
            f"{API_BASE}/tournaments/{tournament_id}/pairings",
            session=self._session,
        )
        if self._delay:
            time.sleep(self._delay)
        return result

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> HttpTournamentSource:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _build_matches(
    tournament_id: str,
    standings: dict[str, dict[str, Any]],
    pairings: list[dict[str, Any]],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], int]:
    matches: list[dict[str, Any]] = []
    skipped_count = 0
    for pairing in parse_pairings(pairings):
        player1 = pairing["player1"]
        player2 = pairing["player2"]
        winner = pairing["winner"]
        if player1 not in standings or player2 not in standings:
            warnings.append(
                f"tournament {tournament_id}: skipped pairing with unknown player"
            )
            skipped_count += 1
            continue
        if winner not in standings:
            warnings.append(
                f"tournament {tournament_id}: skipped pairing with unknown winner "
                f"{winner!r}"
            )
            skipped_count += 1
            continue
        matches.append(
            {
                "deck_a": standings[player1]["deck_id"],
                "deck_b": standings[player2]["deck_id"],
                "winner_deck": standings[winner]["deck_id"],
            }
        )
    return matches, skipped_count


def collect_tournament_dataset(
    options: TournamentCollectionOptions,
    source: TournamentSource,
    output_directory: Path,
    *,
    log: Logger = print,
) -> CollectionResult[TournamentCollectionSummary]:
    selected = select_tournaments(
        source.list_tournaments(max(100, options.max_tournaments)),
        min_players=options.min_players,
        after=options.after,
    )[: options.max_tournaments]
    warnings: list[str] = []
    failures: list[CollectionFailure] = []
    matches: list[dict[str, Any]] = []
    meta: Counter[str] = Counter()
    names: dict[str, str] = {}
    decklists: dict[str, Any] = {}
    included: list[dict[str, Any]] = []
    skipped_count = 0

    for tournament in selected:
        tournament_id = tournament["id"]
        try:
            standings = parse_standings(source.get_standings(tournament_id))
            pairings = source.get_pairings(tournament_id)
        except FetchError as exc:
            failures.append(CollectionFailure(tournament_id, str(exc)))
            log(f"  ! skipped {tournament.get('name', '')}: {exc}")
            continue
        tournament_matches, tournament_skipped = _build_matches(
            tournament_id,
            standings,
            pairings,
            warnings,
        )
        matches.extend(tournament_matches)
        skipped_count += tournament_skipped
        for info in standings.values():
            deck_id = info["deck_id"]
            meta[deck_id] += 1
            names.setdefault(deck_id, info["deck_name"])
            decklists.setdefault(deck_id, info["decklist"])
        included.append(
            {
                "id": tournament_id,
                "name": tournament.get("name"),
                "date": tournament.get("date"),
                "players": tournament.get("players"),
            }
        )

    dataset = {
        "matches": matches,
        "meta": dict(meta),
        "names": names,
        "decklists": decklists,
        "tournaments": included,
    }
    artifact = output_directory / "dataset.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    log(
        f"done: {len(included)}/{len(selected)} tournaments, "
        f"{len(matches)} matches -> {artifact}"
    )
    return CollectionResult(
        collected_count=len(included),
        skipped_count=skipped_count,
        failures=failures,
        warnings=warnings,
        artifacts={"dataset": artifact},
        summary=TournamentCollectionSummary(
            selected_tournaments=len(selected),
            successful_tournament_ids=[item["id"] for item in included],
            failed_tournament_ids=[failure.item_id for failure in failures],
            dataset=dataset,
        ),
    )
