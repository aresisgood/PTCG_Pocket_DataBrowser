"""Limitless 賽事資料:抓取與純函式解析。

用官方 API(play.limitlesstcg.com/api）取得 POCKET 賽事的名次與逐場對戰,
並把它們 join 成「牌組 A vs 牌組 B → 勝方牌組」的對戰紀錄,供勝率分析使用。

解析/select/build 皆為純函式(輸入 JSON、無網路),可對 fixture 做單元測試;
fetch_* 包裝才實際打 API。
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import requests

from .config import DATA_DIR
from .fetch import FetchError, fetch_json

API_BASE = "https://play.limitlesstcg.com/api"
GAME = "POCKET"

# 此 API 的限流較嚴,採較保守的請求間隔。
API_DELAY = 1.2

TOURNAMENTS_DIR = DATA_DIR / "tournaments"
DATASET_JSON = TOURNAMENTS_DIR / "dataset.json"

# winner 欄位的非勝方語意:-1 = 未開打 / 輪空,0 = 平手。
_NON_WINNER = (-1, 0, None)


def select_tournaments(
    tournaments: list[dict[str, Any]],
    *,
    min_players: int = 0,
    after: str | None = None,
) -> list[dict[str, Any]]:
    """依人數與日期篩選賽事清單。

    Args:
        min_players: 只保留參賽人數 >= 此值的賽事。
        after:       只保留日期 >= 此值(ISO 'YYYY-MM-DD'）的賽事;None 不限。
    """
    def keep(t: dict[str, Any]) -> bool:
        if t.get("players", 0) < min_players:
            return False
        if after and t.get("date", "")[:10] < after:
            return False
        return True

    return [t for t in tournaments if keep(t)]


def parse_standings(standings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """把 standings 解析成 {player: {deck_id, deck_name, decklist, record, placing}}。

    未公開牌組(deck 為空）的玩家會被略過,因為無法用於對戰統計。
    """
    parsed: dict[str, dict[str, Any]] = {}
    for row in standings:
        deck = row.get("deck")
        player = row.get("player")
        if not deck or not player:
            continue
        parsed[player] = {
            "deck_id": deck.get("id", ""),
            "deck_name": deck.get("name", ""),
            "decklist": row.get("decklist", {}),
            "record": row.get("record", {}),
            "placing": row.get("placing"),
        }
    return parsed


def parse_pairings(pairings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """只保留有勝負的對戰(排除輪空、平手、未開打）。"""
    decided: list[dict[str, Any]] = []
    for p in pairings:
        if not p.get("player2"):          # 輪空 / bye
            continue
        if p.get("winner") in _NON_WINNER:  # 平手 / 未開打
            continue
        decided.append({
            "player1": p["player1"],
            "player2": p["player2"],
            "winner": p["winner"],
        })
    return decided


def build_matches(
    standings: dict[str, dict[str, Any]],
    pairings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """把逐場對戰 join 上雙方牌組,回傳 {deck_a, deck_b, winner_deck}。

    任一方牌組未知(不在 standings)的對戰會被略過。
    """
    matches: list[dict[str, Any]] = []
    for m in parse_pairings(pairings):
        p1, p2, w = m["player1"], m["player2"], m["winner"]
        if p1 not in standings or p2 not in standings:
            continue
        matches.append({
            "deck_a": standings[p1]["deck_id"],
            "deck_b": standings[p2]["deck_id"],
            "winner_deck": standings[w]["deck_id"],
        })
    return matches


# --- fetch 包裝（實際打 API）--------------------------------------------------

def fetch_tournaments(limit: int = 100, session=None) -> list[dict[str, Any]]:
    """抓取 POCKET 賽事清單。"""
    return fetch_json(f"{API_BASE}/tournaments",
                      params={"game": GAME, "limit": limit}, session=session)


def fetch_standings(tournament_id: str, session=None) -> list[dict[str, Any]]:
    """抓取單一賽事的名次(含牌組）。"""
    return fetch_json(f"{API_BASE}/tournaments/{tournament_id}/standings",
                      session=session)


def fetch_pairings(tournament_id: str, session=None) -> list[dict[str, Any]]:
    """抓取單一賽事的逐場對戰。"""
    return fetch_json(f"{API_BASE}/tournaments/{tournament_id}/pairings",
                      session=session)


def main() -> None:
    """CLI:python -m scraper.tournaments — 抓取近期大型賽事對戰資料。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="抓取近期 POCKET 大型賽事的名次與對戰,整合成 dataset.json。")
    parser.add_argument("--min-players", type=int, default=50)
    parser.add_argument("--after", default=None,
                        help="只納入此日期(YYYY-MM-DD)之後的賽事")
    parser.add_argument("--max", type=int, default=40, dest="max_tournaments")
    args = parser.parse_args()
    collect(min_players=args.min_players, after=args.after,
            max_tournaments=args.max_tournaments)


if __name__ == "__main__":
    main()


def collect(
    *,
    min_players: int = 50,
    after: str | None = None,
    max_tournaments: int = 20,
    session: requests.Session | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """抓取近期大型賽事並整合成分析用資料集。

    回傳(並存到 DATASET_JSON):
        matches     - 所有對戰 {deck_a, deck_b, winner_deck}
        meta        - {deck_id: 使用該原型的玩家數}(當前 Meta 佔比）
        names       - {deck_id: 顯示名稱}
        decklists   - {deck_id: 代表牌表}(供牌組→原型分類）
        tournaments - 納入的賽事 [{id, name, date, players}]
    """
    session = session or requests.Session()
    tours = select_tournaments(fetch_tournaments(session=session),
                               min_players=min_players, after=after)
    tours = tours[:max_tournaments]
    log(f"納入 {len(tours)} 場賽事(min_players={min_players}, after={after})")

    matches: list[dict[str, Any]] = []
    meta: Counter[str] = Counter()
    names: dict[str, str] = {}
    decklists: dict[str, Any] = {}

    used = 0
    for t in tours:
        try:
            standings = parse_standings(fetch_standings(t["id"], session))
            pairings = fetch_pairings(t["id"], session)
        except FetchError as exc:
            # 單場失敗（如限流）不應中斷整批;記錄後跳過。
            log(f"  ! 略過 {t.get('name','')}: {exc}")
            continue
        matches.extend(build_matches(standings, pairings))
        for info in standings.values():
            did = info["deck_id"]
            meta[did] += 1
            names.setdefault(did, info["deck_name"])
            decklists.setdefault(did, info["decklist"])
        used += 1
        log(f"  [{t.get('date','')[:10]}] {t.get('name','')} "
            f"-- {len(standings)} 人")
        time.sleep(API_DELAY)

    dataset = {
        "matches": matches,
        "meta": dict(meta),
        "names": names,
        "decklists": decklists,
        "tournaments": [
            {"id": t["id"], "name": t.get("name"), "date": t.get("date"),
             "players": t.get("players")} for t in tours
        ],
    }
    TOURNAMENTS_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_JSON.write_text(json.dumps(dataset, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    log(f"完成:{used}/{len(tours)} 場賽事、{len(matches)} 場對戰、"
        f"{len(meta)} 種原型 -> {DATASET_JSON}")
    return dataset
