"""爬取流程協調,含 checkpoint 與續爬。

流程:探索卡包 -> 探索卡牌 URL -> 抓取並解析每張卡 -> 驗證 -> 持久化。
每 ``SAVE_EVERY`` 張卡與完成時各寫一次 checkpoint,使中斷的爬取可續跑,
不需重新抓取已完成的卡。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import requests

from .config import (
    CHECKPOINT_JSON, DATA_DIR, FAILED_URLS_JSON, OUTPUT_JSON,
    REQUEST_DELAY, SAVE_EVERY,
)
from .fetch import FetchError, fetch_html
from .models import CardValidationError, validate_card
from .parse import parse_card_page
from .sets import get_all_sets, get_card_urls

Logger = Callable[[str], None]


def _load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    """回傳已爬取的卡牌,以 URL 為 key(無 checkpoint 時回傳空 dict）。"""
    if not path.exists():
        return {}
    cards = json.loads(path.read_text(encoding="utf-8"))
    return {c["url"]: c for c in cards}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def scrape(
    *,
    test_mode: bool = False,
    only_set: str | None = None,
    resume: bool = True,
    log: Logger = print,
) -> list[dict[str, Any]]:
    """執行爬取並回傳收集到的卡牌清單。

    Args:
        test_mode: 只爬前 2 個卡包（快速冒煙測試）。
        only_set:  限定單一卡包 id(例如 "A1"）。
        resume:    沿用既有 checkpoint 並略過已完成的 URL。
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    collected = _load_checkpoint(CHECKPOINT_JSON) if resume else {}
    if collected:
        log(f"[resume] {len(collected)} cards already in checkpoint")

    sets = get_all_sets()
    if only_set:
        sets = [s for s in sets if s["set_id"] == only_set]
    elif test_mode:
        sets = sets[:2]
    log(f"discovered {len(sets)} set(s) to scrape")

    failed: list[str] = []
    session = requests.Session()
    processed_since_save = 0

    for set_info in sets:
        set_id = set_info["set_id"]
        try:
            urls = get_card_urls(set_id)
        except FetchError as exc:
            log(f"[{set_id}] set page failed: {exc}")
            failed.append(f"{set_id} (set page)")
            continue
        log(f"[{set_id}] {set_info['name']} -- {len(urls)} card(s)")

        for url in urls:
            if url in collected:
                continue
            try:
                card = parse_card_page(fetch_html(url, session=session), url)
                validate_card(card)
            except (FetchError, CardValidationError) as exc:
                log(f"  ! {url}: {exc}")
                failed.append(url)
                continue
            collected[url] = card
            processed_since_save += 1
            if processed_since_save >= SAVE_EVERY:
                _write_json(CHECKPOINT_JSON, list(collected.values()))
                processed_since_save = 0
            time.sleep(REQUEST_DELAY)

    cards = list(collected.values())
    _write_json(CHECKPOINT_JSON, cards)
    _write_json(OUTPUT_JSON, cards)
    if failed:
        _write_json(FAILED_URLS_JSON, failed)
    log(f"done: {len(cards)} cards, {len(failed)} failure(s) -> {OUTPUT_JSON}")
    return cards
