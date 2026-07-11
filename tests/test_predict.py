"""analysis.predict 的單元測試(純函式,合成對戰表)。"""
import pytest

from analysis.predict import predict_win_rate

TABLE = {
    "A": {"B": {"wins": 6, "games": 10}, "C": {"wins": 2, "games": 4}},
    "B": {"A": {"wins": 4, "games": 10}},
    "C": {"A": {"wins": 2, "games": 4}},
}
SHARE = {"A": 0.25, "B": 0.5, "C": 0.25}


def test_predict_weights_by_meta_share():
    res = predict_win_rate("A", TABLE, SHARE, min_games=1)
    # A vs B: 0.6 (權重 0.5);A vs C: 0.5 (權重 0.25);A 無鏡像資料。
    # 期望 = (0.6*0.5 + 0.5*0.25) / (0.5+0.25) = 0.425/0.75
    assert round(res["win_rate"], 4) == round(0.425 / 0.75, 4)
    assert res["games"] == 14  # 10 + 4


def test_predict_best_and_worst_matchups():
    res = predict_win_rate("A", TABLE, SHARE, min_games=1)
    assert res["best"][0]["opponent"] == "B"
    assert res["best"][0]["rate"] == 0.6
    assert res["worst"][0]["opponent"] == "C"
    assert res["worst"][0]["rate"] == 0.5


def test_predict_min_games_filters_low_sample():
    # 提高門檻,C(4 場)被排除,只剩 B。
    res = predict_win_rate("A", TABLE, SHARE, min_games=5)
    assert round(res["win_rate"], 4) == 0.6
    assert [m["opponent"] for m in res["best"]] == ["B"]


def test_predict_unknown_deck_returns_low_confidence():
    res = predict_win_rate("ZZZ", TABLE, SHARE, min_games=1)
    assert res["win_rate"] is None
    assert res["games"] == 0
    assert res["best"] == []
