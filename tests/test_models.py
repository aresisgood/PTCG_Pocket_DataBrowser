"""scraper.models 驗證與範本的單元測試。"""
import pytest

from scraper.models import CARD_KEYS, CardValidationError, empty_card, validate_card


def _valid_card() -> dict:
    card = empty_card()
    card.update(name="Bulbasaur", card_type="pokemon", url="x")
    return card


def test_empty_card_has_all_keys_and_is_fresh():
    a, b = empty_card(), empty_card()
    assert set(a) == set(CARD_KEYS)
    a["attacks"].append(1)
    assert b["attacks"] == []  # 不共享可變狀態


def test_validate_accepts_valid_card():
    card = _valid_card()
    assert validate_card(card) is card


def test_validate_rejects_missing_keys():
    card = _valid_card()
    del card["rarity"]
    with pytest.raises(CardValidationError):
        validate_card(card)


def test_validate_rejects_empty_name():
    card = _valid_card()
    card["name"] = ""
    with pytest.raises(CardValidationError):
        validate_card(card)


def test_validate_rejects_bad_card_type():
    card = _valid_card()
    card["card_type"] = "energy"
    with pytest.raises(CardValidationError):
        validate_card(card)
