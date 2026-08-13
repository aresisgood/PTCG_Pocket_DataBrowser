"""Public runtime seam for deck prediction and Meta retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

from .classify import classify_deck
from .predict import predict_win_rate

Confidence = Literal["high", "medium", "low", "unknown"]
ANALYSIS_SCHEMA_VERSION = 1


class AnalysisArtifactError(RuntimeError):
    """A required analysis artifact is malformed or incompatible."""


@dataclass(frozen=True, slots=True)
class PredictionPolicy:
    similarity_threshold: float = 0.4
    min_matchup_games: int = 20
    high_confidence_games: int = 500
    high_confidence_coverage: float = 0.5
    medium_confidence_games: int = 100
    medium_confidence_coverage: float = 0.3
    matchup_result_limit: int = 5


@dataclass(frozen=True, slots=True)
class SourceSummary:
    tournaments: int
    matches: int
    archetypes_total: int
    archetypes_kept: int


@dataclass(frozen=True, slots=True)
class OverallRecord:
    wins: int
    games: int
    rate: float


@dataclass(frozen=True, slots=True)
class ArchetypeRecord:
    name: str
    players: int
    share: float
    overall: OverallRecord | None
    decklist: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MatchupCell:
    wins: int
    games: int

    def __post_init__(self) -> None:
        if self.games < 0 or not 0 <= self.wins <= self.games:
            raise ValueError("wins must be between 0 and games")


@dataclass(frozen=True, slots=True)
class AnalysisSnapshot:
    schema_version: int
    generated_at: str
    source: SourceSummary
    archetypes: dict[str, ArchetypeRecord]
    matchups: dict[str, dict[str, MatchupCell]]

    def __post_init__(self) -> None:
        try:
            datetime.fromisoformat(self.generated_at)
        except (TypeError, ValueError) as exc:
            raise ValueError("generated_at must be ISO-8601") from exc

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisSnapshot:
        version = data.get("schema_version")
        if version != ANALYSIS_SCHEMA_VERSION:
            raise AnalysisArtifactError(
                f"unsupported analysis schema version {version}"
            )
        try:
            source = SourceSummary(**data["source"])
            archetypes = {
                deck_id: ArchetypeRecord(
                    name=row.get("name", deck_id),
                    players=row["players"],
                    share=row["share"],
                    overall=(OverallRecord(**row["overall"])
                             if row.get("overall") else None),
                    decklist=row["decklist"],
                )
                for deck_id, row in data["archetypes"].items()
            }
            matchups = {
                deck_id: {
                    opponent: MatchupCell(**cell)
                    for opponent, cell in opponents.items()
                }
                for deck_id, opponents in data["matchups"].items()
            }
            return cls(
                schema_version=data["schema_version"],
                generated_at=data["generated_at"],
                source=source,
                archetypes=archetypes,
                matchups=matchups,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AnalysisArtifactError(
                f"invalid analysis snapshot: {exc}"
            ) from exc


@dataclass(frozen=True, slots=True)
class ArchetypeIdentity:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class MatchupSummary:
    opponent: str
    name: str
    rate: float
    games: int
    share: float


@dataclass(frozen=True, slots=True)
class Prediction:
    archetype: ArchetypeIdentity | None
    similarity: float
    win_rate: float | None
    ml_win_rate: float | None
    coverage: float
    games: int
    confidence: Confidence
    message: str | None = None
    best: tuple[MatchupSummary, ...] = field(default_factory=tuple)
    worst: tuple[MatchupSummary, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MetaArchetype:
    id: str
    name: str
    share: float
    players: int
    win_rate: float | None
    games: int


@dataclass(frozen=True, slots=True)
class MetaSnapshot:
    generated_at: str
    source: SourceSummary
    archetypes: tuple[MetaArchetype, ...]


class AnalysisEngine:
    """Compose classification, table prediction, optional ML, and policy."""

    def __init__(
        self,
        snapshot: AnalysisSnapshot,
        *,
        card_index: dict[str, dict[str, Any]] | None = None,
        predictor: Any = None,
        policy: PredictionPolicy | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._card_index = card_index or {}
        self._predictor = predictor
        self._policy = policy or PredictionPolicy()

    def predict(self, deck: dict[str, Any] | list[dict[str, Any]]) -> Prediction:
        decklist = self._normalize_decklist(deck)
        references = {
            deck_id: row.decklist
            for deck_id, row in self._snapshot.archetypes.items()
            if row.decklist
        }
        archetype_id, similarity = classify_deck(decklist, references)
        ml_win_rate = self._ml_win_rate(decklist)
        if archetype_id is None or similarity < self._policy.similarity_threshold:
            return Prediction(
                archetype=None,
                similarity=round(similarity, 3),
                win_rate=None,
                ml_win_rate=ml_win_rate,
                coverage=0.0,
                games=0,
                confidence="unknown",
                message="認不出對應原型(自製或資料外牌組）;查表無法預測,"
                        "以下為 ML 模型的估計(僅供參考)。",
            )

        matchup_data = {
            deck_id: {
                opponent: {"wins": cell.wins, "games": cell.games}
                for opponent, cell in opponents.items()
            }
            for deck_id, opponents in self._snapshot.matchups.items()
        }
        shares = {
            deck_id: row.share
            for deck_id, row in self._snapshot.archetypes.items()
        }
        result = predict_win_rate(
            archetype_id,
            matchup_data,
            shares,
            min_games=self._policy.min_matchup_games,
        )
        return Prediction(
            archetype=ArchetypeIdentity(
                archetype_id, self._snapshot.archetypes[archetype_id].name
            ),
            similarity=round(similarity, 3),
            win_rate=result["win_rate"],
            ml_win_rate=ml_win_rate,
            coverage=result["coverage"],
            games=result["games"],
            confidence=self._confidence(result["games"], result["coverage"]),
            best=self._matchup_rows(result["best"]),
            worst=self._matchup_rows(result["worst"]),
        )

    def meta(self) -> MetaSnapshot:
        rows = []
        for deck_id, archetype in self._snapshot.archetypes.items():
            rows.append(
                MetaArchetype(
                    id=deck_id,
                    name=archetype.name,
                    share=archetype.share,
                    players=archetype.players,
                    win_rate=(archetype.overall.rate if archetype.overall else None),
                    games=(archetype.overall.games if archetype.overall else 0),
                )
            )
        rows.sort(key=lambda row: row.share, reverse=True)
        return MetaSnapshot(
            generated_at=self._snapshot.generated_at,
            source=self._snapshot.source,
            archetypes=tuple(rows),
        )

    def _matchup_rows(self, rows: list[dict[str, Any]]) -> tuple[MatchupSummary, ...]:
        return tuple(
            MatchupSummary(
                opponent=row["opponent"],
                name=self._snapshot.archetypes.get(
                    row["opponent"],
                    ArchetypeRecord(row["opponent"], 0, 0.0, None, {}),
                ).name,
                rate=row["rate"],
                games=row["games"],
                share=row["share"],
            )
            for row in rows[: self._policy.matchup_result_limit]
        )

    def _confidence(self, games: int, coverage: float) -> Confidence:
        if (games >= self._policy.high_confidence_games
                and coverage >= self._policy.high_confidence_coverage):
            return "high"
        if (games >= self._policy.medium_confidence_games
                and coverage >= self._policy.medium_confidence_coverage):
            return "medium"
        return "low"

    def _ml_win_rate(self, decklist: dict[str, Any]) -> float | None:
        if self._predictor is None or not self._card_index:
            return None
        shares = {
            deck_id: row.share
            for deck_id, row in self._snapshot.archetypes.items()
        }
        return self._predictor.predict(decklist, self._card_index, shares)

    def _normalize_decklist(
        self, deck: dict[str, Any] | list[dict[str, Any]]
    ) -> dict[str, Any]:
        if isinstance(deck, dict):
            return deck
        pokemon: list[dict[str, Any]] = []
        trainer: list[dict[str, Any]] = []
        for card in deck:
            card_id = f"{card.get('set')}-{card.get('number')}"
            info = self._card_index.get(card_id)
            target = trainer if info and info.get("card_type") == "trainer" else pokemon
            target.append(card)
        return {"pokemon": pokemon, "trainer": trainer}
