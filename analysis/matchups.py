"""由對戰紀錄計算原型對戰矩陣、整體勝率與 Meta 佔比。

輸入的 match 形如 {deck_a, deck_b, winner_deck},皆為純函式,無副作用。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def matchup_table(matches: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
    """建立雙向對戰計數:table[deck][opponent] = {"wins", "games"}。

    每場對戰同時累計雙方視角(deck_a 對 deck_b、以及 deck_b 對 deck_a）。
    """
    table: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"wins": 0, "games": 0}))
    for m in matches:
        a, b, winner = m["deck_a"], m["deck_b"], m["winner_deck"]
        if a == b:
            # 鏡像對戰依定義為 50%:一方勝、一方敗(避免雙視角膨脹成 100%)。
            cell = table[a][a]
            cell["games"] += 2
            cell["wins"] += 1
            continue
        for me, opp in ((a, b), (b, a)):
            cell = table[me][opp]
            cell["games"] += 1
            if winner == me:
                cell["wins"] += 1
    # 轉回普通 dict,避免外部誤觸 defaultdict 自動建鍵。
    return {me: {opp: dict(c) for opp, c in opps.items()}
            for me, opps in table.items()}


def overall_win_rates(matches: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """每個原型跨所有對手的整體 {wins, games, rate}。"""
    agg: dict[str, dict[str, float]] = defaultdict(lambda: {"wins": 0, "games": 0})
    for m in matches:
        a, b, winner = m["deck_a"], m["deck_b"], m["winner_deck"]
        if a == b:
            # 鏡像:一勝一敗,計為 2 場 1 勝(避免膨脹整體勝率)。
            agg[a]["games"] += 2
            agg[a]["wins"] += 1
            continue
        for me in (a, b):
            agg[me]["games"] += 1
            if winner == me:
                agg[me]["wins"] += 1
    result: dict[str, dict[str, float]] = {}
    for deck, v in agg.items():
        games = v["games"]
        result[deck] = {
            "wins": v["wins"],
            "games": games,
            "rate": (v["wins"] / games) if games else 0.0,
        }
    return result


def meta_share(meta_counts: dict[str, int]) -> dict[str, float]:
    """把各原型的玩家數正規化成佔比(總和為 1;空輸入回空 dict）。"""
    total = sum(meta_counts.values())
    if total == 0:
        return {}
    return {deck: count / total for deck, count in meta_counts.items()}
