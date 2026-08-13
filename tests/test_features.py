"""analysis.features 的單元測試(純函式,合成卡片索引)。"""
from analysis.features import (
    FEATURE_NAMES, build_card_index, deck_features, feature_vector,
)

CARD_INDEX = {
    "S-1": {"card_type": "pokemon", "element": "Grass", "hp": 70,
            "stage": "Basic", "ability_name": "", "retreat_cost": 1,
            "name": "Bulba"},
    "S-2": {"card_type": "pokemon", "element": "Fire", "hp": 120,
            "stage": "Stage 2", "ability_name": "Blaze", "retreat_cost": 2,
            "name": "Charizard ex"},
    "T-1": {"card_type": "trainer", "name": "Potion", "trainer_type": "Item"},
}

DECKLIST = {
    "pokemon": [{"set": "S", "number": "1", "count": 2},
                {"set": "S", "number": "2", "count": 1}],
    "trainer": [{"set": "T", "number": "1", "count": 2}],
}


def test_deck_features_counts_and_stats():
    f = deck_features(DECKLIST, CARD_INDEX)
    assert f["ele_Grass"] == 2
    assert f["ele_Fire"] == 1
    assert f["n_pokemon"] == 3
    assert f["n_trainer"] == 2
    assert f["n_ex"] == 1
    assert f["n_basic"] == 2
    assert f["n_stage2"] == 1
    assert f["n_ability"] == 1
    assert f["hp_total"] == 260
    assert round(f["hp_avg"], 2) == 86.67
    assert round(f["retreat_avg"], 3) == 1.333
    assert f["n_distinct"] == 3


def test_unknown_cards_are_ignored_for_attributes():
    dl = {"pokemon": [{"set": "Z", "number": "9", "count": 2}], "trainer": []}
    f = deck_features(dl, CARD_INDEX)
    assert f["n_pokemon"] == 2          # 仍計入張數
    assert f["hp_total"] == 0           # 但查不到屬性 -> 不貢獻 HP
    assert f["ele_Grass"] == 0


def test_feature_vector_matches_feature_names_order():
    vec = feature_vector(DECKLIST, CARD_INDEX)
    assert len(vec) == len(FEATURE_NAMES)
    f = deck_features(DECKLIST, CARD_INDEX)
    assert vec == [f[name] for name in FEATURE_NAMES]


def test_card_index_uses_one_shared_set_number_identity_rule():
    cards = [{"set_id": "P-A", "number": "007", "name": "Research"}]

    assert build_card_index(cards) == {"P-A-007": cards[0]}
