"""載入 data/analysis.json,提供預測所需的對戰表、Meta 佔比與原型參考牌表。

在程序啟動時載入一次;測試可用 FastAPI 的 dependency_overrides 換掉。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scraper.config import DATA_DIR

ANALYSIS_JSON = DATA_DIR / "analysis.json"
CARDS_JSON = DATA_DIR / "cards.json"
MODEL_PATH = DATA_DIR / "model.joblib"


class AnalysisStore:
    """把 analysis.json 拆成方便查詢的結構,並選配 ML 模型與卡片索引。"""

    def __init__(self, data: dict[str, Any],
                 card_index: dict[str, dict[str, Any]] | None = None,
                 model: Any = None):
        archetypes: dict[str, Any] = data.get("archetypes", {})
        self.archetypes = archetypes
        self.matchups = data.get("matchups", {})
        self.source = data.get("source", {})
        self.references = {
            aid: a["decklist"] for aid, a in archetypes.items() if a.get("decklist")
        }
        self.share = {aid: a.get("share", 0.0) for aid, a in archetypes.items()}
        self.names = {aid: a.get("name", aid) for aid, a in archetypes.items()}
        self.card_index = card_index or {}
        self.model = model  # analysis.model.WinModel | None

    def name_of(self, deck_id: str) -> str:
        return self.names.get(deck_id, deck_id)


def _load_card_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    cards = json.loads(path.read_text(encoding="utf-8"))
    return {f"{c['set_id']}-{c['number']}": c for c in cards}


def load_store(path: Path = ANALYSIS_JSON) -> AnalysisStore:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    card_index = _load_card_index(CARDS_JSON)
    model = None
    if MODEL_PATH.exists():
        from analysis.model import WinModel  # 延遲載入,避免無模型時強依賴
        model = WinModel.load(MODEL_PATH)
    return AnalysisStore(data, card_index, model)


_store: AnalysisStore | None = None


def get_store() -> AnalysisStore:
    """FastAPI 相依:回傳(快取的)分析資料。"""
    global _store
    if _store is None:
        _store = load_store()
    return _store
