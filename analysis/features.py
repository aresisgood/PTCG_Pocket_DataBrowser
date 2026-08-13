"""把一副牌組轉成固定長度的數值特徵向量,供 ML 模型使用。

特徵以卡片組成為基礎(屬性分布、EX 數、進化階段、HP、撤退、特性、張數),
不含原型 id,因此模型學到的是牌組「內容」的模式,能推廣到未見過的牌組。
"""
from __future__ import annotations

from typing import Any

# 固定的屬性順序(對應 cards.json 的 element)。
ELEMENTS = ("Grass", "Fire", "Water", "Lightning", "Psychic",
            "Fighting", "Darkness", "Metal", "Dragon", "Fairy", "Colorless")

# 特徵欄位的固定順序(feature_vector 依此輸出)。
FEATURE_NAMES = (
    *(f"ele_{e}" for e in ELEMENTS),
    "n_pokemon", "n_trainer", "n_ex", "n_basic", "n_stage1", "n_stage2",
    "n_ability", "hp_total", "hp_avg", "retreat_avg", "n_distinct",
)


def card_identity(set_id: object, number: object) -> str:
    """Return the one canonical card identity used by training and runtime."""
    return f"{set_id}-{number}"


def catalog_card_identity(card: dict[str, Any]) -> str:
    return card_identity(card["set_id"], card["number"])


def deck_card_identity(card: dict[str, Any]) -> str:
    return card_identity(card.get("set"), card.get("number"))


def build_card_index(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index catalog rows by the shared card identity rule."""
    return {catalog_card_identity(card): card for card in cards}


def deck_features(decklist: dict[str, Any],
                  card_index: dict[str, dict[str, Any]]) -> dict[str, float]:
    """由牌表 + 卡片索引算出具名特徵 dict(FEATURE_NAMES 為鍵)。"""
    f: dict[str, float] = {name: 0.0 for name in FEATURE_NAMES}
    hp_sum = 0.0
    retreat_sum = 0.0
    distinct = 0

    for card in decklist.get("pokemon", []) or []:
        count = card.get("count", 1)
        distinct += 1
        f["n_pokemon"] += count
        info = card_index.get(deck_card_identity(card))
        if not info:
            continue  # 查不到屬性的卡:只計張數,不貢獻其餘特徵
        element = info.get("element")
        if element in ELEMENTS:
            f[f"ele_{element}"] += count
        hp_sum += (info.get("hp") or 0) * count
        retreat_sum += (info.get("retreat_cost") or 0) * count
        stage = info.get("stage", "")
        if stage == "Basic":
            f["n_basic"] += count
        elif stage == "Stage 1":
            f["n_stage1"] += count
        elif stage == "Stage 2":
            f["n_stage2"] += count
        if info.get("ability_name"):
            f["n_ability"] += count
        if str(info.get("name", "")).lower().endswith(" ex"):
            f["n_ex"] += count

    for card in decklist.get("trainer", []) or []:
        f["n_trainer"] += card.get("count", 1)
        distinct += 1

    n_pokemon = f["n_pokemon"]
    f["hp_total"] = hp_sum
    f["hp_avg"] = hp_sum / n_pokemon if n_pokemon else 0.0
    f["retreat_avg"] = retreat_sum / n_pokemon if n_pokemon else 0.0
    f["n_distinct"] = distinct
    return f


def feature_vector(decklist: dict[str, Any],
                   card_index: dict[str, dict[str, Any]]) -> list[float]:
    """回傳與 FEATURE_NAMES 對齊的數值特徵向量。"""
    f = deck_features(decklist, card_index)
    return [f[name] for name in FEATURE_NAMES]
