"""由原型對戰表 + 當前 Meta 佔比,估算某原型的預期勝率。

預期勝率 = Σ(對各對手勝率 × 該對手 Meta 佔比) / Σ(有資料對手的佔比)。
一律附上支撐樣本數(信心度)與最有利/最不利對戰,避免給出假裝很準的單一數字。
"""
from __future__ import annotations

from typing import Any


def predict_win_rate(
    deck_id: str,
    matchup_table: dict[str, dict[str, dict[str, int]]],
    meta_share: dict[str, float],
    *,
    min_games: int = 5,
) -> dict[str, Any]:
    """估算 ``deck_id`` 對當前 Meta 的預期勝率。

    Args:
        min_games: 對戰樣本數低於此門檻的對手不納入(避免雜訊)。

    回傳:
        win_rate  - 加權預期勝率(無任何可用對戰時為 None)
        coverage  - 納入計算的對手其 Meta 佔比總和(0~1,信心度指標）
        games     - 支撐這些對戰的總場數
        best/worst- 依勝率排序的對戰明細 [{opponent, rate, games, share}]
    """
    opponents = matchup_table.get(deck_id, {})
    weighted_sum = 0.0
    weight_total = 0.0
    total_games = 0
    rows: list[dict[str, Any]] = []

    for opp, share in meta_share.items():
        cell = opponents.get(opp)
        if not cell or cell["games"] < min_games:
            continue
        rate = cell["wins"] / cell["games"]
        weighted_sum += rate * share
        weight_total += share
        total_games += cell["games"]
        rows.append({"opponent": opp, "rate": rate,
                     "games": cell["games"], "share": share})

    win_rate = (weighted_sum / weight_total) if weight_total else None
    rows_by_rate = sorted(rows, key=lambda r: r["rate"], reverse=True)
    return {
        "win_rate": win_rate,
        "coverage": weight_total,
        "games": total_games,
        "best": rows_by_rate,
        "worst": list(reversed(rows_by_rate)),
    }
