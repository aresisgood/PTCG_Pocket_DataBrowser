"""把賽事資料集整合成前端/API 使用的分析成品 data/analysis.json。

組合 matchups 的純函式,並只保留有意義的原型(玩家數達門檻)作為分類參考,
避免一次性冷門牌污染分類與檔案大小。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from project_config import ANALYSIS_JSON

from .matchups import matchup_table, meta_share, overall_win_rates



def build_analysis(dataset: dict[str, Any], *,
                   min_archetype_players: int = 5) -> dict[str, Any]:
    """由 dataset(collect 的輸出)計算對戰表與原型摘要。"""
    matches = dataset["matches"]
    meta = dataset["meta"]
    names = dataset.get("names", {})
    decklists = dataset.get("decklists", {})

    overall = overall_win_rates(matches)
    share = meta_share(meta)

    archetypes: dict[str, Any] = {}
    for deck_id, players in meta.items():
        if players < min_archetype_players:
            continue
        archetypes[deck_id] = {
            "name": names.get(deck_id, deck_id),
            "players": players,
            "share": share.get(deck_id, 0.0),
            "overall": overall.get(deck_id),
            "decklist": decklists.get(deck_id, {}),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "tournaments": len(dataset.get("tournaments", [])),
            "matches": len(matches),
            "archetypes_total": len(meta),
            "archetypes_kept": len(archetypes),
        },
        "archetypes": archetypes,
        "matchups": matchup_table(matches),
    }


def build_from_file(dataset_path, out_path=ANALYSIS_JSON, *,
                    min_archetype_players: int = 5) -> dict[str, Any]:
    """讀取 dataset.json、計算分析、寫出 analysis.json。"""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    analysis = build_analysis(dataset, min_archetype_players=min_archetype_players)
    out_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return analysis
