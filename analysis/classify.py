"""把一副牌組分類到最接近的已知原型(以卡片組成的重疊度）。

用 Jaccard 相似度(交集 / 聯集)比對卡片集合;不看張數,只看牌組用了哪些卡。
自製、認不出的牌組會得到偏低的相似度,呼叫端可據此標為低信心。
"""
from __future__ import annotations

from typing import Any


def deck_card_ids(decklist: dict[str, Any]) -> set[str]:
    """從牌表(pokemon + trainer)萃取卡片識別碼集合 {"set-number", ...}。"""
    ids: set[str] = set()
    for group in ("pokemon", "trainer"):
        for card in decklist.get(group, []) or []:
            set_id, number = card.get("set"), card.get("number")
            if set_id and number is not None:
                ids.add(f"{set_id}-{number}")
    return ids


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def classify_deck(
    decklist: dict[str, Any],
    references: dict[str, dict[str, Any]],
) -> tuple[str | None, float]:
    """回傳 (最接近的原型 id, 相似度);無參考資料時回 (None, 0.0)。"""
    target = deck_card_ids(decklist)
    best_id: str | None = None
    best_sim = 0.0
    for deck_id, ref_decklist in references.items():
        sim = _jaccard(target, deck_card_ids(ref_decklist))
        if sim > best_sim:
            best_id, best_sim = deck_id, sim
    return best_id, best_sim
