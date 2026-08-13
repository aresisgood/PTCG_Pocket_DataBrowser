"""CLI:python -m analysis — 由 dataset.json 重算 data/analysis.json。"""
from __future__ import annotations

import argparse

from project_config import TOURNAMENT_DATASET_JSON as DATASET_JSON

from .build import ANALYSIS_JSON, build_from_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="由賽事資料集重算勝率分析成品 analysis.json。")
    parser.add_argument("--min-players", type=int, default=5,
                        dest="min_archetype_players",
                        help="納入分析的原型最低玩家數(過濾冷門牌）")
    args = parser.parse_args()
    result = build_from_file(DATASET_JSON, ANALYSIS_JSON,
                             min_archetype_players=args.min_archetype_players)
    src = result["source"]
    print(f"analysis.json 已更新:保留 {src['archetypes_kept']}/"
          f"{src['archetypes_total']} 種原型、{src['matches']} 場對戰 "
          f"-> {ANALYSIS_JSON}")


if __name__ == "__main__":
    main()
