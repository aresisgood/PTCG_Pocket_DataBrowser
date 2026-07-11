"""scraper.pipeline 的離線流程協調測試。

網路（fetch_html）與探索（get_all_sets/get_card_urls）皆以 monkeypatch
替換,使續爬/checkpoint/驗證略過的邏輯不需連上線上網站即可被測試。
"""
import json
from pathlib import Path

import pytest

from scraper import pipeline

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def wired(monkeypatch, tmp_path):
    """把 pipeline 指向暫存資料夾,並把網路 stub 掉。"""
    monkeypatch.setattr(pipeline, "DATA_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "OUTPUT_JSON", tmp_path / "cards.json")
    monkeypatch.setattr(pipeline, "CHECKPOINT_JSON", tmp_path / "cards.checkpoint.json")
    monkeypatch.setattr(pipeline, "FAILED_URLS_JSON", tmp_path / "failed.json")
    monkeypatch.setattr(pipeline, "REQUEST_DELAY", 0)  # 測試中不 sleep

    html = (FIXTURES / "pokemon_basic_A1_1.html").read_text(encoding="utf-8")
    urls = ["https://pocket.limitlesstcg.com/cards/A1/1",
            "https://pocket.limitlesstcg.com/cards/A1/2"]

    monkeypatch.setattr(pipeline, "get_all_sets",
                        lambda: [{"set_id": "A1", "name": "Genetic Apex"}])
    monkeypatch.setattr(pipeline, "get_card_urls", lambda set_id: urls)
    # 兩個 URL 都回傳同一張 Bulbasaur 頁面,但各自帶有自己的 url 引數。
    monkeypatch.setattr(pipeline, "fetch_html",
                        lambda url, session=None: html)
    return tmp_path


def test_scrape_writes_output_and_checkpoint(wired):
    cards = pipeline.scrape(resume=False, log=lambda *_: None)
    assert len(cards) == 2
    assert (wired / "cards.json").exists()
    saved = json.loads((wired / "cards.json").read_text(encoding="utf-8"))
    assert {c["url"] for c in saved} == {
        "https://pocket.limitlesstcg.com/cards/A1/1",
        "https://pocket.limitlesstcg.com/cards/A1/2",
    }
    assert all(c["rarity"] for c in saved)  # 真實解析出的資料有流經整條流程


def test_scrape_resumes_from_checkpoint(wired, monkeypatch):
    # 預先塞入一個 checkpoint,內含兩個 URL 之一。
    existing = [{"url": "https://pocket.limitlesstcg.com/cards/A1/1",
                 "name": "Bulbasaur"}]
    (wired / "cards.checkpoint.json").write_text(
        json.dumps(existing), encoding="utf-8")

    fetched: list[str] = []
    real_html = (FIXTURES / "pokemon_basic_A1_1.html").read_text(encoding="utf-8")

    def spy(url, session=None):
        fetched.append(url)
        return real_html

    monkeypatch.setattr(pipeline, "fetch_html", spy)
    cards = pipeline.scrape(resume=True, log=lambda *_: None)

    assert len(cards) == 2
    # 只有尚未爬取的 URL 應該被抓取。
    assert fetched == ["https://pocket.limitlesstcg.com/cards/A1/2"]


def test_scrape_records_validation_failures(wired, monkeypatch):
    # 沒有 .card-text 的頁面會產生無法解析（不合法）的卡。
    monkeypatch.setattr(pipeline, "fetch_html",
                        lambda url, session=None: "<html><body>nope</body></html>")
    cards = pipeline.scrape(resume=False, log=lambda *_: None)
    assert cards == []
    assert (wired / "failed.json").exists()
