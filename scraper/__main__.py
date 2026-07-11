"""CLI:python -m scraper [--test] [--set A1] [--no-resume]。

``pipeline.scrape`` 的精簡引數解析包裝。
"""
from __future__ import annotations

import argparse

from .pipeline import scrape


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape PTCG Pocket cards.")
    parser.add_argument("--test", action="store_true",
                        help="只爬前 2 個卡包（冒煙測試）")
    parser.add_argument("--set", dest="only_set", metavar="SET_ID",
                        help="只爬單一卡包,例如 A1")
    parser.add_argument("--no-resume", dest="resume", action="store_false",
                        help="忽略既有 checkpoint")
    args = parser.parse_args()
    scrape(test_mode=args.test, only_set=args.only_set, resume=args.resume)


if __name__ == "__main__":
    main()
