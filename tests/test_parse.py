"""scraper.parse.parse_card_page 的單元測試。

測試針對儲存的真實 HTML fixture(tests/fixtures/*.html）執行,把解析器
契約釘在實際的 pocket.limitlesstcg.com 標記上,且完全不涉及網路。
預期值皆由線上頁面人工核對而來。
"""
from pathlib import Path

import pytest

from scraper.parse import parse_card_page

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


@pytest.fixture
def bulbasaur() -> dict:
    return parse_card_page(load("pokemon_basic_A1_1"),
                           "https://pocket.limitlesstcg.com/cards/A1/1")


@pytest.fixture
def gardevoir() -> dict:
    return parse_card_page(load("pokemon_ability_A1_132"),
                           "https://pocket.limitlesstcg.com/cards/A1/132")


@pytest.fixture
def koga() -> dict:
    return parse_card_page(load("trainer_A1_222"),
                           "https://pocket.limitlesstcg.com/cards/A1/222")


@pytest.fixture
def mewtwo_crown() -> dict:
    return parse_card_page(load("pokemon_crown_A1_286"),
                           "https://pocket.limitlesstcg.com/cards/A1/286")


# --- 基本寶可夢卡 -------------------------------------------------------------

def test_basic_pokemon_identity(bulbasaur):
    assert bulbasaur["name"] == "Bulbasaur"
    assert bulbasaur["card_type"] == "pokemon"
    assert bulbasaur["trainer_type"] == ""
    assert bulbasaur["set_id"] == "A1"
    assert bulbasaur["set_name"] == "Genetic Apex"
    assert bulbasaur["number"] == "1"


def test_basic_pokemon_stats(bulbasaur):
    assert bulbasaur["element"] == "Grass"
    assert bulbasaur["stage"] == "Basic"
    assert bulbasaur["hp"] == 70
    assert bulbasaur["weakness"] == "Fire"
    assert bulbasaur["retreat_cost"] == 1
    assert bulbasaur["evolves_from"] == ""


def test_basic_pokemon_attack(bulbasaur):
    assert bulbasaur["attacks"] == [
        {"cost": ["G", "C"], "name": "Vine Whip", "damage": "40", "effect": ""}
    ]
    assert bulbasaur["ability_name"] == ""
    assert bulbasaur["ability_text"] == ""


def test_basic_pokemon_meta(bulbasaur):
    assert bulbasaur["illustrator"] == "Narumi Sato"
    assert bulbasaur["rarity"] == "One Diamond"
    assert bulbasaur["pack"] == "Mewtwo"
    assert bulbasaur["image_url"] == (
        "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket/A1/A1_001_EN_SM.webp"
    )


# --- 有特性的進化寶可夢卡 -----------------------------------------------------

def test_ability_pokemon_evolution(gardevoir):
    assert gardevoir["name"] == "Gardevoir"
    assert gardevoir["element"] == "Psychic"
    assert gardevoir["stage"] == "Stage 2"
    assert gardevoir["hp"] == 110
    assert gardevoir["evolves_from"] == "Kirlia"
    assert gardevoir["weakness"] == "Darkness"
    assert gardevoir["retreat_cost"] == 2


def test_ability_pokemon_ability(gardevoir):
    assert gardevoir["ability_name"] == "Psy Shadow"
    assert gardevoir["ability_text"].startswith("Once during your turn")


def test_ability_pokemon_attack(gardevoir):
    assert gardevoir["attacks"][0] == {
        "cost": ["P", "P", "C"], "name": "Psyshot", "damage": "60", "effect": ""
    }
    assert gardevoir["rarity"] == "Three Diamond"


# --- 文字型稀有度（Crown Rare 沒有 ◊/☆ 符號，而是純文字）---------------------

def test_crown_rare_text_rarity(mewtwo_crown):
    assert mewtwo_crown["name"] == "Mewtwo ex"
    assert mewtwo_crown["rarity"] == "Crown Rare"
    assert mewtwo_crown["pack"] == ""  # Crown Rare 不屬於任何卡包


def test_promo_source_is_not_rarity():
    # 促銷卡的取得來源（Wonder Pick）不是稀有度，應歸為來源（pack）而非 rarity。
    card = parse_card_page(load("promo_wonderpick_PB_7"),
                           "https://pocket.limitlesstcg.com/cards/P-B/7")
    assert card["name"] == "Torchic"
    assert card["rarity"] == ""
    assert card["pack"] == "Wonder Pick"


# --- 訓練家卡 -----------------------------------------------------------------

def test_trainer_identity(koga):
    assert koga["name"] == "Koga"
    assert koga["card_type"] == "trainer"
    assert koga["trainer_type"] == "Supporter"
    assert koga["element"] == ""
    assert koga["stage"] == ""
    assert koga["hp"] is None
    assert koga["attacks"] == []


def test_trainer_effect(koga):
    assert koga["effect"] == (
        "Put your Muk or Weezing in the Active Spot into your hand."
    )
    assert koga["rarity"] == "Two Diamond"
    assert koga["pack"] == "Mewtwo"
    assert koga["illustrator"] == "Souichirou Gunjima"


# --- schema 欄位齊全 ----------------------------------------------------------

REQUIRED_KEYS = {
    "url", "set_id", "number", "name", "card_type", "trainer_type", "element",
    "stage", "evolves_from", "hp", "weakness", "retreat_cost", "ability_name",
    "ability_text", "attacks", "effect", "rarity", "pack", "illustrator",
    "set_name", "image_url",
}


def test_all_keys_present(bulbasaur, gardevoir, koga):
    for card in (bulbasaur, gardevoir, koga):
        assert REQUIRED_KEYS <= set(card), REQUIRED_KEYS - set(card)
        assert card["url"].startswith("https://pocket.limitlesstcg.com/cards/")
