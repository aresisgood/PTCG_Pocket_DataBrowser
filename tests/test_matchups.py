"""analysis.matchups 的單元測試（純函式,合成資料,結果可完全預期）。"""
import pytest

from analysis.matchups import matchup_table, meta_share, overall_win_rates

MATCHES = [
    {"deck_a": "A", "deck_b": "B", "winner_deck": "A"},
    {"deck_a": "A", "deck_b": "B", "winner_deck": "B"},
    {"deck_a": "B", "deck_b": "A", "winner_deck": "A"},  # A 對 B 共 2 勝 1 敗
    {"deck_a": "A", "deck_b": "C", "winner_deck": "C"},  # A 對 C 0 勝 1 敗
]


def test_matchup_table_counts_both_directions():
    t = matchup_table(MATCHES)
    assert t["A"]["B"] == {"wins": 2, "games": 3}
    assert t["B"]["A"] == {"wins": 1, "games": 3}
    assert t["A"]["C"] == {"wins": 0, "games": 1}
    assert t["C"]["A"] == {"wins": 1, "games": 1}


def test_overall_win_rates():
    o = overall_win_rates(MATCHES)
    assert o["A"] == {"wins": 2, "games": 4, "rate": 0.5}
    assert o["C"]["rate"] == 1.0
    assert round(o["B"]["rate"], 3) == 0.333


def test_mirror_match_is_fifty_percent():
    # 鏡像對戰(同原型)依定義必為 50%,不可因雙視角計數而膨脹成 100%。
    mirror = [{"deck_a": "A", "deck_b": "A", "winner_deck": "A"}]
    t = matchup_table(mirror)
    assert t["A"]["A"] == {"wins": 1, "games": 2}  # rate 0.5
    o = overall_win_rates(mirror)
    assert o["A"] == {"wins": 1, "games": 2, "rate": 0.5}


def test_meta_share_normalizes():
    share = meta_share({"A": 3, "B": 1})
    assert share == {"A": 0.75, "B": 0.25}


def test_meta_share_empty():
    assert meta_share({}) == {}
