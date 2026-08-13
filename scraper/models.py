"""卡牌 schema 與驗證。

權威的卡牌紀錄是純 ``dict``（可 JSON 序列化、對前端友善）。``empty_card``
提供一個依慣例不可變的範本,讓每張解析出的卡都帶有完整欄位;
``validate_card`` 則在卡牌被持久化前,於系統邊界強制執行最低契約。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

# 完整欄位集合。順序對齊既有的 ptcgpocket_cards.json 以維持連續性,
# 並在最後附加 image_url。
@dataclass(slots=True)
class CardSchema:
    """Authoritative field and default definition for card artifacts."""

    url: str = ""
    set_id: str = ""
    number: str = ""
    name: str = ""
    card_type: str = ""
    trainer_type: str = ""
    element: str = ""
    stage: str = ""
    evolves_from: str = ""
    hp: int | None = None
    weakness: str = ""
    retreat_cost: int = 0
    ability_name: str = ""
    ability_text: str = ""
    attacks: list[dict[str, Any]] = field(default_factory=list)
    effect: str = ""
    rarity: str = ""
    pack: str = ""
    illustrator: str = ""
    set_name: str = ""
    image_url: str = ""


CARD_KEYS: tuple[str, ...] = tuple(item.name for item in fields(CardSchema))

# 能量字母 -> 屬性名稱（limitlesstcg 使用的 PTCG 字型編碼）。
ENERGY_MAP: dict[str, str] = {
    "G": "Grass", "R": "Fire", "W": "Water", "L": "Lightning",
    "P": "Psychic", "F": "Fighting", "D": "Darkness", "M": "Metal",
    "Y": "Fairy", "N": "Dragon", "C": "Colorless",
}


def empty_card() -> dict[str, Any]:
    """回傳一個所有欄位皆已預設的全新卡牌 dict。

    永遠回傳新物件,呼叫端絕不會共享可變狀態。
    """
    return asdict(CardSchema())


class CardValidationError(ValueError):
    """在解析出的卡牌未通過最低 schema 契約時拋出。"""


def validate_card(card: dict[str, Any]) -> dict[str, Any]:
    """在持久化邊界驗證卡牌;原樣回傳。

    以清晰訊息快速失敗,而非默默持久化垃圾資料。
    """
    missing = set(CARD_KEYS) - set(card)
    if missing:
        raise CardValidationError(f"missing keys: {sorted(missing)}")
    if not card["name"]:
        raise CardValidationError(f"empty name for {card.get('url') or '?'}")
    if card["card_type"] not in ("pokemon", "trainer"):
        raise CardValidationError(
            f"bad card_type {card['card_type']!r} for {card['url']}"
        )
    if not isinstance(card["attacks"], list):
        raise CardValidationError(f"attacks must be a list for {card['url']}")
    return card
