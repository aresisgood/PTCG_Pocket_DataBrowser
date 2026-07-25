"""勝率預測與 Meta 端點。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from analysis.classify import classify_deck
from analysis.features import feature_vector
from analysis.predict import predict_win_rate

from ..analysis_store import AnalysisStore, get_store
from ..schemas import CardInput, PredictRequest

router = APIRouter(prefix="/api", tags=["predict"])

# 分類相似度低於此值時,視為認不出的自製牌組(低信心）。
_MIN_SIMILARITY = 0.4
# 對戰樣本數門檻,低於此不納入預測。
_MIN_GAMES = 20


def _to_decklist(cards: list[CardInput],
                 store: AnalysisStore) -> dict[str, Any]:
    """把前端的扁平卡片清單依卡種拆成牌表結構(供特徵/分類使用）。"""
    pokemon: list[dict[str, Any]] = []
    trainer: list[dict[str, Any]] = []
    for card in cards:
        row = card.model_dump(exclude_none=True)
        info = store.card_index.get(f"{card.set}-{card.number}")
        target = trainer if info and info.get("card_type") == "trainer" else pokemon
        target.append(row)
    return {"pokemon": pokemon, "trainer": trainer}


def _enrich(row: dict[str, Any], store: AnalysisStore) -> dict[str, Any]:
    return {**row, "name": store.name_of(row["opponent"])}


def _ml_win_rate(decklist: dict[str, Any], store: AnalysisStore) -> float | None:
    """以 ML 模型估算對當前 Meta 的預期勝率(無模型時回 None)。"""
    if not store.model or not store.card_index:
        return None
    feat = feature_vector(decklist, store.card_index)
    return store.model.deck_win_rate(feat, store.model.features, store.share)


@router.post("/predict")
def predict(req: PredictRequest, store: AnalysisStore = Depends(get_store)):
    decklist = _to_decklist(req.cards, store)
    archetype_id, similarity = classify_deck(decklist, store.references)
    ml_win = _ml_win_rate(decklist, store)  # 即使認不出原型也能算

    if archetype_id is None or similarity < _MIN_SIMILARITY:
        return {
            "archetype": None,
            "similarity": round(similarity, 3),
            "win_rate": None,
            "ml_win_rate": ml_win,
            "confidence": "unknown",
            "message": "認不出對應原型(自製或資料外牌組）;查表無法預測,"
                       "以下為 ML 模型的估計(僅供參考)。",
            "best": [], "worst": [],
        }

    result = predict_win_rate(archetype_id, store.matchups, store.share,
                              min_games=_MIN_GAMES)
    return {
        "archetype": {"id": archetype_id, "name": store.name_of(archetype_id)},
        "similarity": round(similarity, 3),
        "win_rate": result["win_rate"],
        "ml_win_rate": ml_win,
        "coverage": result["coverage"],
        "games": result["games"],
        "confidence": _confidence(result["games"], result["coverage"]),
        "best": [_enrich(m, store) for m in result["best"][:5]],
        "worst": [_enrich(m, store) for m in result["worst"][:5]],
    }


@router.get("/meta")
def meta(store: AnalysisStore = Depends(get_store)):
    """當前 Meta 原型列表(佔比 + 整體勝率),依佔比排序。"""
    rows = []
    for aid, a in store.archetypes.items():
        overall = a.get("overall") or {}
        rows.append({
            "id": aid,
            "name": a.get("name", aid),
            "share": a.get("share", 0.0),
            "players": a.get("players", 0),
            "win_rate": overall.get("rate"),
            "games": overall.get("games", 0),
        })
    rows.sort(key=lambda r: r["share"], reverse=True)
    return {"source": store.source, "archetypes": rows}


def _confidence(games: int, coverage: float) -> str:
    if games >= 500 and coverage >= 0.5:
        return "high"
    if games >= 100 and coverage >= 0.3:
        return "medium"
    return "low"
