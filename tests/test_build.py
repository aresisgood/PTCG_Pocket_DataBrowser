"""analysis.build 的單元測試(合成 dataset）。"""
from analysis.build import build_analysis

DATASET = {
    "matches": [
        {"deck_a": "A", "deck_b": "B", "winner_deck": "A"},
        {"deck_a": "A", "deck_b": "B", "winner_deck": "A"},
    ],
    "meta": {"A": 6, "B": 6, "rare": 2},  # rare 低於門檻
    "names": {"A": "Deck A", "B": "Deck B", "rare": "Rare Deck"},
    "decklists": {"A": {"pokemon": []}, "B": {"pokemon": []}, "rare": {}},
    "tournaments": [{"id": "t1"}],
}


def test_build_keeps_only_archetypes_above_threshold():
    out = build_analysis(DATASET, min_archetype_players=5)
    assert set(out["archetypes"]) == {"A", "B"}   # rare(2 人)被濾掉
    assert out["source"]["archetypes_total"] == 3
    assert out["source"]["archetypes_kept"] == 2


def test_build_includes_matchups_and_meta():
    out = build_analysis(DATASET, min_archetype_players=5)
    assert out["matchups"]["A"]["B"] == {"wins": 2, "games": 2}
    assert out["archetypes"]["A"]["name"] == "Deck A"
    assert 0 < out["archetypes"]["A"]["share"] < 1
