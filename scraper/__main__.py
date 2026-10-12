"""CLI:python -m scraper [--test] [--set A1] [--no-resume]。

``pipeline.scrape`` 的精簡引數解析包裝。
"""
from __future__ import annotations

import argparse

from project_config import DATA_DIR

from .card_catalog import (
    CardCollectionOptions,
    CollectionError,
    CollectionInterrupted,
    HttpCardSource,
    collect_card_catalog,
)


def _report_interrupt(interrupt: CollectionInterrupted) -> None:
    print(
        f"已中斷：已抓取 {interrupt.collected_count} 張新卡，"
        f"{interrupt.failure_count} 張抓取失敗"
    )
    if interrupt.progress_path is None:
        print("沒有任何卡片被蒐集，權威檔案未被修改")
        return
    if interrupt.resumable:
        print(f"進度已寫回 {interrupt.progress_path}，重新執行即可續爬")
        return
    print(f"進度暫存在 {interrupt.progress_path}（僅供檢查，不會自動續用）")
    print("重新執行（不加 --no-resume）會從既有 checkpoint 續爬")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape PTCG Pocket cards.")
    parser.add_argument("--test", action="store_true",
                        help="只爬前 2 個卡包（冒煙測試）")
    parser.add_argument("--set", dest="only_set", metavar="SET_ID",
                        help="只爬單一卡包,例如 A1")
    parser.add_argument("--no-resume", dest="resume", action="store_false",
                        help="忽略既有 checkpoint")
    parser.add_argument("--allow-shrink", action="store_true",
                        help="允許發布比既有 data/cards.json 更少的卡片")
    args = parser.parse_args()
    options = CardCollectionOptions(
        test_mode=args.test,
        only_set=args.only_set,
        resume=args.resume,
        allow_shrink=args.allow_shrink,
    )
    try:
        with HttpCardSource() as source:
            collect_card_catalog(options, source, DATA_DIR)
    except CollectionInterrupted as interrupt:
        _report_interrupt(interrupt)
        raise SystemExit(130) from None
    except KeyboardInterrupt:
        # Ctrl+C outside the gathering loop: while the checkpoint is being read,
        # between the publish writes, or a second Ctrl+C during a progress flush.
        # Every file is written atomically, so none can be half-written, but the
        # publish may have got partway through its three artifacts.
        print("已中斷：蒐集流程在收尾階段被中斷")
        print("每個檔案本身都完整（原子寫入），但可能只有部分檔案更新了")
        print("請確認 data/cards.json 與 data/cards.checkpoint.json 的張數是否符合預期")
        raise SystemExit(130) from None
    except CollectionError as error:
        print(f"蒐集中止：{error}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
