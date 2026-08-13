"""analysis.build 的單元測試(合成 dataset）。"""
from datetime import datetime, timezone

from analysis.build import build_analysis
from analysis.runtime import AnalysisSnapshot

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
    assert set(out.archetypes) == {"A", "B"}   # rare(2 人)被濾掉
    assert out.source.archetypes_total == 3
    assert out.source.archetypes_kept == 2


def test_build_includes_matchups_and_meta():
    out = build_analysis(DATASET, min_archetype_players=5)
    assert out.matchups["A"]["B"].wins == 2
    assert out.matchups["A"]["B"].games == 2
    assert out.archetypes["A"].name == "Deck A"
    assert 0 < out.archetypes["A"].share < 1


def test_build_returns_versioned_snapshot_with_injected_clock():
    now = datetime(2026, 8, 13, 1, 2, 3, tzinfo=timezone.utc)

    out = build_analysis(DATASET, clock=lambda: now)

    assert isinstance(out, AnalysisSnapshot)
    assert out.schema_version == 1
    assert out.generated_at == "2026-08-13T01:02:03+00:00"
    assert out.to_dict() == {
        "schema_version": 1,
        "generated_at": "2026-08-13T01:02:03+00:00",
        "source": {"tournaments": 1, "matches": 2,
                   "archetypes_total": 3, "archetypes_kept": 2},
        "archetypes": {
            "A": {"name": "Deck A", "players": 6,
                  "share": 0.42857142857142855,
                  "overall": {"wins": 2, "games": 2, "rate": 1.0},
                  "decklist": {"pokemon": []}},
            "B": {"name": "Deck B", "players": 6,
                  "share": 0.42857142857142855,
                  "overall": {"wins": 0, "games": 2, "rate": 0.0},
                  "decklist": {"pokemon": []}},
        },
        "matchups": {
            "A": {"B": {"wins": 2, "games": 2}},
            "B": {"A": {"wins": 0, "games": 2}},
        },
    }
