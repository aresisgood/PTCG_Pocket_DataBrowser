"""scraper.tournaments 純函式的單元測試。

針對儲存的真實 Limitless API 回應 fixture(tests/fixtures/api/*.json）執行,
把賽事清單篩選、standings/pairings 解析,以及對戰 join 的契約釘在實際資料上,
完全不涉及網路。預期值由 fixture 人工核對而來。
"""
import json
from pathlib import Path

import pytest

from scraper.tournaments import (
    build_matches, parse_pairings, parse_standings, select_tournaments,
)

FX = Path(__file__).parent / "fixtures" / "api"


def load(name: str):
    return json.loads((FX / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def standings():
    return load("standings")


@pytest.fixture
def pairings():
    return load("pairings")


# --- select_tournaments ------------------------------------------------------

def test_select_filters_by_min_players():
    tl = load("tournaments_list")  # players: [49,122,34,216,7,98,72,10]
    picked = select_tournaments(tl, min_players=50)
    assert len(picked) == 4
    assert all(t["players"] >= 50 for t in picked)


def test_select_filters_by_after_date():
    sample = [
        {"id": "a", "players": 100, "date": "2026-05-01T00:00:00.000Z"},
        {"id": "b", "players": 100, "date": "2026-07-01T00:00:00.000Z"},
    ]
    picked = select_tournaments(sample, min_players=0, after="2026-06-01")
    assert [t["id"] for t in picked] == ["b"]


# --- parse_standings ---------------------------------------------------------

def test_parse_standings_keys_by_player(standings):
    parsed = parse_standings(standings)
    assert len(parsed) == 45
    champ = parsed["santymcgoob"]
    assert champ["deck_id"] == "mega-gardevoir-ex-b2-mega-diancie-ex-b3b"
    assert champ["placing"] == 1
    assert champ["record"] == {"wins": 9, "losses": 0, "ties": 0}
    assert "pokemon" in champ["decklist"]


def test_parse_standings_skips_undisclosed_decks():
    raw = [
        {"player": "a", "deck": {"id": "x", "name": "X"}, "decklist": {},
         "placing": 1, "record": {}},
        {"player": "b", "deck": None, "decklist": {}, "placing": 2, "record": {}},
    ]
    parsed = parse_standings(raw)
    assert set(parsed) == {"a"}  # player with no deck is dropped


# --- parse_pairings ----------------------------------------------------------

def test_parse_pairings_keeps_only_decided(pairings):
    decided = parse_pairings(pairings)
    assert len(decided) == 104  # 114 total minus byes / ties / not-played
    for m in decided:
        assert m["player2"]                       # no byes
        assert m["winner"] in (m["player1"], m["player2"])


def test_parse_pairings_excludes_byes_ties_unplayed():
    raw = [
        {"player1": "a", "player2": "b", "winner": "a"},   # decided
        {"player1": "c", "winner": -1},                     # bye / not played
        {"player1": "d", "player2": "e", "winner": 0},      # tie
        {"player1": "f", "player2": "g", "winner": -1},     # not played
    ]
    decided = parse_pairings(raw)
    assert [m["winner"] for m in decided] == ["a"]


# --- build_matches (join standings x pairings) -------------------------------

def test_build_matches_joins_decks(standings, pairings):
    matches = build_matches(parse_standings(standings), pairings)
    assert len(matches) == 104
    assert matches[0] == {
        "deck_a": "hisuian-zoroark-ex-b3b-sunflora-b1a",
        "deck_b": "zoroark-ex-b3-darkrai-ex-a2",
        "winner_deck": "zoroark-ex-b3-darkrai-ex-a2",
    }


def test_build_matches_skips_unknown_deck_players():
    parsed = {"a": {"deck_id": "deckA"}, "b": {"deck_id": "deckB"}}
    raw_pairings = [
        {"player1": "a", "player2": "b", "winner": "a"},   # both known
        {"player1": "a", "player2": "zzz", "winner": "a"},  # zzz not in standings
    ]
    matches = build_matches(parsed, raw_pairings)
    assert matches == [
        {"deck_a": "deckA", "deck_b": "deckB", "winner_deck": "deckA"}
    ]


def test_build_matches_skips_unknown_winner():
    parsed = {"a": {"deck_id": "deckA"}, "b": {"deck_id": "deckB"}}
    raw_pairings = [
        {"player1": "a", "player2": "b", "winner": "missing"},
    ]

    assert build_matches(parsed, raw_pairings) == []
