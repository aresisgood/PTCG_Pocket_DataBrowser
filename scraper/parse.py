"""pocket.limitlesstcg.com 卡牌頁面的純 HTML -> 卡牌 dict 解析。

``parse_card_page`` 接收 HTML 字串(完全不涉及網路),因此可對儲存的
fixture 完整做單元測試。每次呼叫都建立自己的 soup,並回傳全新的卡牌
dict;不共享任何可變狀態。
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .models import empty_card

_URL_RE = re.compile(r"/cards/([^/]+)/(\d+)")
_HP_RE = re.compile(r"(\d+)\s*HP")
_WEAKNESS_RE = re.compile(r"Weakness:\s*([^\s]+)")
_RETREAT_RE = re.compile(r"Retreat:\s*(\d+)")
_DAMAGE_RE = re.compile(r"\s(\d+[+×x]*)$")

_DIAMOND = "◊"  # 鑽石符號 ◊
_STAR = "☆"      # 星星符號 ☆
_CROWN = "♛"     # 皇冠符號 ♛

_DIAMOND_NAMES = {1: "One Diamond", 2: "Two Diamond",
                  3: "Three Diamond", 4: "Four Diamond"}
_STAR_NAMES = {1: "One Star", 2: "Two Star", 3: "Three Star"}

# 會各自獨立解析的子區塊;若某個 plain section 不含以下任何一種,
# 就視為卡牌的規則/效果文字(訓練家卡、道具卡）。
_SPECIAL_SECTION_SELECTOR = (
    ".card-text-title, .card-text-attack, .card-text-ability, "
    ".card-text-wrr, .card-text-artist, .card-text-flavor"
)


def _norm(text: str) -> str:
    """把所有連續空白（含換行）壓縮成單一空格。"""
    return " ".join(text.split())


def _rarity_from_symbol(symbol: str) -> str:
    diamonds = symbol.count(_DIAMOND)
    stars = symbol.count(_STAR)
    if diamonds:
        return _DIAMOND_NAMES.get(diamonds, f"{diamonds} Diamond")
    if stars:
        return _STAR_NAMES.get(stars, f"{stars} Star")
    if _CROWN in symbol or "\U0001f451" in symbol:
        return "Crown"
    return ""


def _parse_type(type_el, card: dict[str, Any]) -> None:
    """從 type 區塊填入 card_type / trainer_type / stage / evolves_from。"""
    parts = [p.strip() for p in _norm(type_el.get_text()).split(" - ") if p.strip()]
    if not parts:
        return
    head = parts[0]
    if head.startswith("Pok"):  # "Pokémon"
        card["card_type"] = "pokemon"
        for p in parts[1:]:
            if p.startswith("Evolves from"):
                continue
            if not card["stage"]:
                card["stage"] = p
        link = type_el.select_one("a")
        if link:
            card["evolves_from"] = link.get_text(strip=True)
    elif head.startswith("Trainer"):
        card["card_type"] = "trainer"
        if len(parts) > 1:
            card["trainer_type"] = parts[1]


def _parse_title(title_el, card: dict[str, Any]) -> None:
    """從 title 區塊填入 element 與 hp（僅寶可夢卡）。"""
    normalized = _norm(title_el.get_text())
    hp_match = _HP_RE.search(normalized)
    if hp_match:
        card["hp"] = int(hp_match.group(1))
    if card["card_type"] != "pokemon":
        return
    # 名稱之後的部分:"Name - Element - NN HP"
    parts = [p.strip() for p in normalized.split(" - ")[1:]]
    for p in parts:
        if _HP_RE.search(p) or not p:
            continue
        card["element"] = p
        break


def _parse_attacks(card_text) -> list[dict[str, Any]]:
    attacks: list[dict[str, Any]] = []
    for atk in card_text.select(".card-text-attack"):
        info = atk.select_one(".card-text-attack-info")
        if info is None:
            continue
        symbol_el = info.select_one(".ptcg-symbol")
        cost = list(symbol_el.get_text(strip=True)) if symbol_el else []
        full = _norm(info.get_text())
        symbol_text = symbol_el.get_text(strip=True) if symbol_el else ""
        rest = full[len(symbol_text):].strip() if full.startswith(symbol_text) else full
        dmg_match = _DAMAGE_RE.search(rest)
        if dmg_match:
            damage = dmg_match.group(1)
            name = rest[: dmg_match.start()].strip()
        else:
            damage, name = "", rest
        effect_el = atk.select_one(".card-text-attack-effect")
        effect = _norm(effect_el.get_text()) if effect_el else ""
        attacks.append({"cost": cost, "name": name, "damage": damage, "effect": effect})
    return attacks


def _parse_ability(card_text, card: dict[str, Any]) -> None:
    ability = card_text.select_one(".card-text-ability")
    if ability is None:
        return
    info = ability.select_one(".card-text-ability-info")
    if info is not None:
        card["ability_name"] = _norm(info.get_text()).replace("Ability:", "").strip()
    effect = ability.select_one(".card-text-ability-effect")
    if effect is not None:
        card["ability_text"] = _norm(effect.get_text())


def _parse_effect(card_text) -> str:
    """純規則文字(訓練家 / 道具):不含任何特殊子區塊的 section。"""
    parts: list[str] = []
    for sec in card_text.select(".card-text-section"):
        if sec.select_one(_SPECIAL_SECTION_SELECTOR):
            continue
        classes = sec.get("class", [])
        if any(c != "card-text-section" for c in classes):
            continue
        txt = _norm(sec.get_text())
        if txt:
            parts.append(txt)
    return " ".join(parts)


def _parse_prints(soup, card: dict[str, Any]) -> None:
    prints = soup.select_one(".card-prints-current")
    if prints is None:
        return
    set_name_el = prints.select_one(".text-lg")
    if set_name_el is not None:
        card["set_name"] = re.sub(r"\s*\(.*\)\s*$", "", _norm(set_name_el.get_text()))
    for span in prints.select(".prints-current-details span"):
        text = _norm(span.get_text())
        if "#" not in text:
            continue
        tokens = [t.strip() for t in text.split("·")]  # 中間點 ·
        for tok in tokens[1:]:
            if tok.endswith("pack"):
                card["pack"] = tok[: -len("pack")].strip()
            elif not card["rarity"] and (_DIAMOND in tok or _STAR in tok
                                         or _CROWN in tok or "\U0001f451" in tok):
                card["rarity"] = _rarity_from_symbol(tok)
            elif not card["rarity"] and tok.endswith("Rare"):
                # 文字型稀有度（無 ◊/☆ 符號），例如 "Crown Rare"。
                card["rarity"] = tok
            elif not card["pack"] and tok:
                # 其他取得來源（Wonder Pick / Shop / Missions…），非稀有度。
                card["pack"] = tok
        break


def parse_card_page(html: str, url: str) -> dict[str, Any]:
    """把單張卡牌詳情頁解析成卡牌 dict。

    Args:
        html: /cards/{set}/{number} 頁面的原始 HTML。
        url:  來源 URL(用於填入 set_id/number,並作為出處紀錄）。
    """
    soup = BeautifulSoup(html, "html.parser")
    card = empty_card()
    card["url"] = url

    url_match = _URL_RE.search(url)
    if url_match:
        card["set_id"], card["number"] = url_match.group(1), url_match.group(2)

    card_text = soup.select_one(".card-text")
    if card_text is None:
        return card  # 無法解析的頁面 -> 由呼叫端 / 驗證流程標記

    name_el = card_text.select_one(".card-text-name")
    if name_el is not None:
        card["name"] = name_el.get_text(strip=True)

    type_el = card_text.select_one(".card-text-type")
    if type_el is not None:
        _parse_type(type_el, card)

    title_el = card_text.select_one(".card-text-title")
    if title_el is not None:
        _parse_title(title_el, card)

    wrr = card_text.select_one(".card-text-wrr")
    if wrr is not None:
        wrr_text = _norm(wrr.get_text())
        weakness = _WEAKNESS_RE.search(wrr_text)
        retreat = _RETREAT_RE.search(wrr_text)
        if weakness:
            card["weakness"] = weakness.group(1)
        if retreat:
            card["retreat_cost"] = int(retreat.group(1))

    card["attacks"] = _parse_attacks(card_text)
    _parse_ability(card_text, card)
    card["effect"] = _parse_effect(card_text)

    artist = card_text.select_one(".card-text-artist")
    if artist is not None:
        card["illustrator"] = _norm(artist.get_text()).replace("Illustrated by", "").strip()

    image = soup.select_one(".card-image img")
    if image is not None:
        card["image_url"] = image.get("src", "")

    _parse_prints(soup, card)
    return card