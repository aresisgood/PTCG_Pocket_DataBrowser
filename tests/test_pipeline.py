"""Compatibility coverage for the historical card scraper entry point."""

from pathlib import Path

from scraper.card_catalog import InMemoryCardSource
from scraper.pipeline import scrape

FIXTURES = Path(__file__).parent / "fixtures"


def test_scrape_delegates_to_public_collection_workflow(tmp_path):
    url = "https://pocket.limitlesstcg.com/cards/A1/1"
    source = InMemoryCardSource(
        sets=[{"set_id": "A1", "name": "Genetic Apex"}],
        card_urls={"A1": [url]},
        card_pages={
            url: (FIXTURES / "pokemon_basic_A1_1.html").read_text(encoding="utf-8")
        },
    )

    cards = scrape(
        resume=False,
        source=source,
        output_directory=tmp_path,
        log=lambda *_: None,
    )

    assert [card["name"] for card in cards] == ["Bulbasaur"]
