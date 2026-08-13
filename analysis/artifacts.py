"""Filesystem adapters for validated analysis runtime artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from .features import build_card_index
from .model import WinModel
from .runtime import AnalysisArtifactError, AnalysisEngine, AnalysisSnapshot


def load_snapshot(path: Path) -> AnalysisSnapshot:
    if not path.is_file():
        raise AnalysisArtifactError(f"analysis snapshot not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisArtifactError(f"invalid analysis snapshot {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AnalysisArtifactError(f"invalid analysis snapshot {path}: root must be object")
    return AnalysisSnapshot.from_dict(data)


def load_engine(
    snapshot_path: Path,
    *,
    cards_path: Path,
    model_path: Path,
) -> AnalysisEngine:
    snapshot = load_snapshot(snapshot_path)
    card_index: dict[str, dict] = {}
    if cards_path.is_file():
        try:
            cards = json.loads(cards_path.read_text(encoding="utf-8"))
            if not isinstance(cards, list):
                raise TypeError("card catalog root must be list")
            card_index = build_card_index(cards)
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AnalysisArtifactError(f"invalid card catalog {cards_path}: {exc}") from exc
    predictor = WinModel.load(model_path) if model_path.is_file() else None
    return AnalysisEngine(snapshot, card_index=card_index, predictor=predictor)
