"""卡牌 schema 與驗證。

``CardSchema`` 是欄位、預設值與靜態型別的單一權威定義，也提供 mapping
相容介面給 parser 使用。持久化邊界透過 ``to_dict`` 產生既有 JSON shape。
"""
from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from dataclasses import asdict, dataclass, field, fields
from typing import Any

# 完整欄位集合。順序對齊既有的 ptcgpocket_cards.json 以維持連續性,
# 並在最後附加 image_url。
@dataclass(slots=True)
class CardSchema(MutableMapping[str, Any]):
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

    def __getitem__(self, key: str) -> Any:
        if key not in CARD_KEYS or not hasattr(self, key):
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in CARD_KEYS:
            raise KeyError(key)
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        if key not in CARD_KEYS or not hasattr(self, key):
            raise KeyError(key)
        delattr(self, key)

    def __iter__(self) -> Iterator[str]:
        return (key for key in CARD_KEYS if hasattr(self, key))

    def __len__(self) -> int:
        return sum(hasattr(self, key) for key in CARD_KEYS)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardSchema:
        unknown = set(data) - set(CARD_KEYS)
        if unknown:
            raise ValueError(f"unknown card keys: {sorted(unknown)}")
        card = cls()
        card.update(data)
        return card


CARD_KEYS: tuple[str, ...] = tuple(item.name for item in fields(CardSchema))

# 能量字母 -> 屬性名稱（limitlesstcg 使用的 PTCG 字型編碼）。
ENERGY_MAP: dict[str, str] = {
    "G": "Grass", "R": "Fire", "W": "Water", "L": "Lightning",
    "P": "Psychic", "F": "Fighting", "D": "Darkness", "M": "Metal",
    "Y": "Fairy", "N": "Dragon", "C": "Colorless",
}


def empty_card() -> CardSchema:
    """回傳一個所有欄位皆已預設的全新卡牌物件。

    永遠回傳新物件,呼叫端絕不會共享可變狀態。
    """
    return CardSchema()


class CardValidationError(ValueError):
    """在解析出的卡牌未通過最低 schema 契約時拋出。"""


def validate_card(card: CardSchema) -> CardSchema:
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
