"""Card catalog collection through its public workflow seam."""

import json
from pathlib import Path

from scraper.card_catalog import (
    CardCollectionOptions,
    CollectionError,
    HttpCardSource,
    InMemoryCardSource,
    collect_card_catalog,
)
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _source():
    url = "https://pocket.limitlesstcg.com/cards/A1/1"
    html = (FIXTURES / "pokemon_basic_A1_1.html").read_text(encoding="utf-8")
    return InMemoryCardSource(
        sets=[{"set_id": "A1", "name": "Genetic Apex"}],
        card_urls={"A1": [url]},
        card_pages={url: html},
    )


def test_clean_run_overwrites_stale_failure_artifact(tmp_path):
    failure_path = tmp_path / "failed_urls.json"
    failure_path.write_text('["old-failure"]', encoding="utf-8")

    result = collect_card_catalog(
        CardCollectionOptions(resume=False), _source(), tmp_path
    )

    assert result.collected_count == 1
    assert result.failures == []
    assert json.loads(failure_path.read_text(encoding="utf-8")) == []
    assert set(result.summary["cards"][0]) == {
        "url", "set_id", "number", "name", "card_type", "trainer_type",
        "element", "stage", "evolves_from", "hp", "weakness",
        "retreat_cost", "ability_name", "ability_text", "attacks", "effect",
        "rarity", "pack", "illustrator", "set_name", "image_url",
    }


class TrackingSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_http_source_closes_only_an_internally_created_session(monkeypatch):
    created = TrackingSession()
    monkeypatch.setattr("scraper.card_catalog.requests.Session", lambda: created)

    internal = HttpCardSource(delay=0)
    internal.close()
    assert created.closed is True

    supplied = TrackingSession()
    external = HttpCardSource(session=supplied, delay=0)
    external.close()
    assert supplied.closed is False


def test_resume_uses_checkpoint_without_refetching_card(tmp_path):
    url = "https://pocket.limitlesstcg.com/cards/A1/1"
    existing = {"url": url, "name": "Existing"}
    (tmp_path / "cards.checkpoint.json").write_text(
        json.dumps([existing]), encoding="utf-8"
    )
    source = InMemoryCardSource(
        sets=[{"set_id": "A1", "name": "Genetic Apex"}],
        card_urls={"A1": [url]},
        card_pages={},
    )

    result = collect_card_catalog(CardCollectionOptions(), source, tmp_path)

    assert result.summary["cards"] == [existing]


def test_malformed_checkpoint_raises_clear_collection_error(tmp_path):
    (tmp_path / "cards.checkpoint.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(CollectionError, match="malformed checkpoint"):
        collect_card_catalog(CardCollectionOptions(), _source(), tmp_path)
