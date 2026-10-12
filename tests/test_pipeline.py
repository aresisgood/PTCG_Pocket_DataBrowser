"""Compatibility coverage for the historical card scraper entry point."""

from pathlib import Path

import pytest

from scraper.card_catalog import CollectionInterrupted, InMemoryCardSource
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


def test_scrape_propagates_an_operator_interrupt(tmp_path):
    url = "https://pocket.limitlesstcg.com/cards/A1/1"
    source = InMemoryCardSource(
        sets=[{"set_id": "A1", "name": "Genetic Apex"}],
        card_urls={"A1": [url]},
        card_pages={url: KeyboardInterrupt()},
    )

    with pytest.raises(CollectionInterrupted) as excinfo:
        scrape(
            resume=False,
            source=source,
            output_directory=tmp_path,
            log=lambda *_: None,
        )

    assert excinfo.value.collected_count == 0
    assert excinfo.value.resumable is False


def test_scrape_builds_its_own_http_source_when_none_is_supplied(monkeypatch, tmp_path):
    url = "https://pocket.limitlesstcg.com/cards/A1/1"
    html = (FIXTURES / "pokemon_basic_A1_1.html").read_text(encoding="utf-8")
    closed = []

    class RecordingSource(InMemoryCardSource):
        def close(self):
            closed.append(True)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    monkeypatch.setattr(
        "scraper.pipeline.HttpCardSource",
        lambda: RecordingSource(
            sets=[{"set_id": "A1", "name": "Genetic Apex"}],
            card_urls={"A1": [url]},
            card_pages={url: html},
        ),
    )

    cards = scrape(resume=False, output_directory=tmp_path, log=lambda *_: None)

    assert [card["name"] for card in cards] == ["Bulbasaur"]
    assert closed == [True]
