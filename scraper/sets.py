"""探索:列出擴充卡包,以及每個卡包內的卡牌 URL。

解析函式接收 HTML 字串（純函式);而 fetch+parse 的便利包裝則透過
fetch 層取得 HTML。
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .config import BASE_URL, CARDS_INDEX_URL
from .fetch import fetch_html


def parse_sets(html: str) -> list[dict[str, Any]]:
    """把 /cards 索引頁解析成卡包描述清單。

    每一項:{"set_id", "name", "release_date", "card_count"}。
    """
    soup = BeautifulSoup(html, "html.parser")
    sets: list[dict[str, Any]] = []
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if not cols:
            continue
        link = cols[0].find("a")
        if not link or not link.get("href"):
            continue
        set_id = link["href"].rstrip("/").rsplit("/", 1)[-1]
        full_text = " ".join(cols[0].get_text(" ", strip=True).split())
        # 儲存格文字為 "<名稱> <set_id>";去掉結尾的 id 以取得名稱。
        name = re.sub(rf"\s*{re.escape(set_id)}\s*$", "", full_text).strip()
        count = 0
        if len(cols) >= 3:
            digits = re.sub(r"\D", "", cols[2].get_text())
            count = int(digits) if digits else 0
        sets.append({
            "set_id": set_id,
            "name": name,
            "release_date": cols[1].get_text(strip=True) if len(cols) >= 2 else "",
            "card_count": count,
        })
    return sets


def parse_card_urls(html: str, set_id: str) -> list[str]:
    """把某個卡包頁面解析成有序的卡牌詳情 URL 清單。"""
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"^/cards/{re.escape(set_id)}/\d+$")
    seen: dict[str, None] = {}  # 保留順序、去除重複
    for a in soup.select("a[href]"):
        href = a["href"]
        if pattern.match(href):
            seen[BASE_URL + href] = None
    return list(seen)


def get_all_sets() -> list[dict[str, Any]]:
    """抓取並解析完整的卡包清單。"""
    return parse_sets(fetch_html(CARDS_INDEX_URL))


def get_card_urls(set_id: str) -> list[str]:
    """抓取並解析單一卡包的卡牌 URL。"""
    return parse_card_urls(fetch_html(f"{CARDS_INDEX_URL}/{set_id}"), set_id)
