"""Card catalog collection through its public workflow seam."""

import json
from pathlib import Path

from scraper import card_catalog
from scraper.card_catalog import (
    CardCollectionOptions,
    CollectionError,
    CollectionInterrupted,
    HttpCardSource,
    InMemoryCardSource,
    collect_card_catalog,
)
from scraper.fetch import FetchError
from scraper.models import CARD_KEYS, CardSchema
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
    assert isinstance(result.summary.cards[0], CardSchema)
    assert set(result.summary.cards[0]) == set(CARD_KEYS)


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

    assert [card.url for card in result.summary.cards] == [url]
    assert result.summary.cards[0].name == "Existing"
    assert result.collected_count == 0
    assert result.skipped_count == 1


def test_malformed_checkpoint_raises_clear_collection_error(tmp_path):
    (tmp_path / "cards.checkpoint.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(CollectionError, match="malformed checkpoint"):
        collect_card_catalog(CardCollectionOptions(), _source(), tmp_path)


def test_card_failure_is_reported_without_discarding_success(tmp_path):
    good_url = "https://pocket.limitlesstcg.com/cards/A1/1"
    bad_url = "https://pocket.limitlesstcg.com/cards/A1/2"
    source = _source()
    source.card_urls["A1"] = [good_url, bad_url]
    source.card_pages[bad_url] = FetchError("unavailable")

    result = collect_card_catalog(
        CardCollectionOptions(resume=False), source, tmp_path
    )

    assert result.collected_count == 1
    assert result.skipped_count == 0
    assert [failure.item_id for failure in result.failures] == [bad_url]
    assert [card["url"] for card in result.summary.cards] == [good_url]


def _two_card_source_interrupting_on_second():
    """A source that yields one card, then is interrupted by the operator."""
    good_url = "https://pocket.limitlesstcg.com/cards/A1/1"
    interrupted_url = "https://pocket.limitlesstcg.com/cards/A1/2"
    source = _source()
    source.card_urls["A1"] = [good_url, interrupted_url]
    source.card_pages[interrupted_url] = KeyboardInterrupt()
    return source, good_url


def test_fresh_run_interrupt_keeps_canonical_checkpoint_intact(tmp_path):
    checkpoint_path = tmp_path / "cards.checkpoint.json"
    complete_catalog = [{"url": "https://example.test/old", "name": "Complete"}]
    checkpoint_path.write_text(json.dumps(complete_catalog), encoding="utf-8")
    source, good_url = _two_card_source_interrupting_on_second()

    with pytest.raises(CollectionInterrupted):
        collect_card_catalog(
            CardCollectionOptions(resume=False, save_every=1), source, tmp_path
        )

    assert json.loads(checkpoint_path.read_text(encoding="utf-8")) == complete_catalog
    staged = json.loads(
        (tmp_path / "cards.fresh.checkpoint.json").read_text(encoding="utf-8")
    )
    assert [card["url"] for card in staged] == [good_url]


def test_interrupt_leaves_published_catalog_untouched(tmp_path):
    output_path = tmp_path / "cards.json"
    published = [{"url": "https://example.test/published", "name": "Published"}]
    output_path.write_text(json.dumps(published), encoding="utf-8")
    source, _ = _two_card_source_interrupting_on_second()

    with pytest.raises(CollectionInterrupted):
        collect_card_catalog(
            CardCollectionOptions(resume=False), source, tmp_path
        )

    assert json.loads(output_path.read_text(encoding="utf-8")) == published


def test_resume_run_interrupt_flushes_progress_to_checkpoint(tmp_path):
    checkpoint_path = tmp_path / "cards.checkpoint.json"
    source, good_url = _two_card_source_interrupting_on_second()

    with pytest.raises(CollectionInterrupted):
        collect_card_catalog(CardCollectionOptions(), source, tmp_path)

    flushed = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert [card["url"] for card in flushed] == [good_url]


def test_interrupt_error_reports_recovery_location(tmp_path):
    source, _ = _two_card_source_interrupting_on_second()

    with pytest.raises(CollectionInterrupted) as excinfo:
        collect_card_catalog(
            CardCollectionOptions(resume=False), source, tmp_path
        )

    assert excinfo.value.collected_count == 1
    assert excinfo.value.progress_path == tmp_path / "cards.fresh.checkpoint.json"
    assert "cards.fresh.checkpoint.json" in str(excinfo.value)


def test_completed_fresh_run_promotes_and_clears_staging_checkpoint(tmp_path):
    result = collect_card_catalog(
        CardCollectionOptions(resume=False, save_every=1), _source(), tmp_path
    )

    assert not (tmp_path / "cards.fresh.checkpoint.json").exists()
    promoted = json.loads(
        (tmp_path / "cards.checkpoint.json").read_text(encoding="utf-8")
    )
    assert len(promoted) == 1
    assert result.artifacts["checkpoint"] == tmp_path / "cards.checkpoint.json"

class InterruptingSetsSource:
    """A source interrupted while it is still listing sets."""

    def list_sets(self):
        raise KeyboardInterrupt()

    def list_card_urls(self, set_id):
        raise AssertionError("must not reach set pages")

    def get_card_page(self, url):
        raise AssertionError("must not reach card pages")


def test_interrupt_while_listing_sets_is_reported_as_collection_interrupt(tmp_path):
    with pytest.raises(CollectionInterrupted) as excinfo:
        collect_card_catalog(
            CardCollectionOptions(resume=False), InterruptingSetsSource(), tmp_path
        )

    assert excinfo.value.collected_count == 0
    assert excinfo.value.progress_path is None
    assert list(tmp_path.iterdir()) == []


def test_interrupt_flushes_progress_before_any_periodic_save(tmp_path):
    source, good_url = _two_card_source_interrupting_on_second()

    with pytest.raises(CollectionInterrupted):
        collect_card_catalog(CardCollectionOptions(resume=False), source, tmp_path)

    staged = json.loads(
        (tmp_path / "cards.fresh.checkpoint.json").read_text(encoding="utf-8")
    )
    assert [card["url"] for card in staged] == [good_url]


def test_interrupt_reports_failures_seen_so_far(tmp_path):
    failing_url = "https://pocket.limitlesstcg.com/cards/A1/3"
    source, _ = _two_card_source_interrupting_on_second()
    source.card_urls["A1"] = [failing_url] + source.card_urls["A1"]
    source.card_pages[failing_url] = FetchError("unavailable")
    messages = []

    with pytest.raises(CollectionInterrupted) as excinfo:
        collect_card_catalog(
            CardCollectionOptions(resume=False), source, tmp_path, log=messages.append
        )

    assert excinfo.value.failure_count == 1
    assert "1 failure(s)" in messages[-1]
    assert not (tmp_path / "failed_urls.json").exists()


def test_publish_refuses_to_shrink_an_existing_catalog(tmp_path):
    output_path = tmp_path / "cards.json"
    published = [
        {"url": f"https://example.test/{index}", "name": "Complete"}
        for index in range(5)
    ]
    output_path.write_text(json.dumps(published), encoding="utf-8")

    with pytest.raises(CollectionError, match="refusing to shrink"):
        collect_card_catalog(CardCollectionOptions(resume=False), _source(), tmp_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == published
    assert not (tmp_path / "cards.checkpoint.json").exists()
    staged = json.loads(
        (tmp_path / "cards.fresh.checkpoint.json").read_text(encoding="utf-8")
    )
    assert len(staged) == 1


def test_publish_accepts_a_catalog_that_does_not_shrink(tmp_path):
    output_path = tmp_path / "cards.json"
    output_path.write_text('[{"url": "https://example.test/0"}]', encoding="utf-8")

    result = collect_card_catalog(
        CardCollectionOptions(resume=False), _source(), tmp_path
    )

    assert result.collected_count == 1
    assert len(json.loads(output_path.read_text(encoding="utf-8"))) == 1


def test_successful_run_clears_a_stale_staging_checkpoint(tmp_path):
    url = "https://pocket.limitlesstcg.com/cards/A1/1"
    staging_path = tmp_path / "cards.fresh.checkpoint.json"
    staging_path.write_text('[{"url": "stale", "name": "Stale"}]', encoding="utf-8")
    checkpoint_path = tmp_path / "cards.checkpoint.json"
    checkpoint_path.write_text(
        json.dumps([{"url": url, "name": "Existing"}]), encoding="utf-8"
    )
    source = InMemoryCardSource(
        sets=[{"set_id": "A1", "name": "Genetic Apex"}],
        card_urls={"A1": [url]},
        card_pages={},
    )

    collect_card_catalog(CardCollectionOptions(), source, tmp_path)

    assert not staging_path.exists()
    assert len(json.loads(checkpoint_path.read_text(encoding="utf-8"))) == 1


def test_write_failure_leaves_the_previous_artifact_intact(tmp_path, monkeypatch):
    target = tmp_path / "cards.json"
    previous = [{"url": "https://example.test/keep", "name": "Keep"}]
    target.write_text(json.dumps(previous), encoding="utf-8")

    def failing_replace(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(card_catalog.os, "replace", failing_replace)

    with pytest.raises(OSError):
        card_catalog._write_json(target, [{"url": "https://example.test/new"}])

    assert json.loads(target.read_text(encoding="utf-8")) == previous

def _failing_source():
    """A source whose every card fetch fails."""
    source = _source()
    for url in source.card_urls["A1"]:
        source.card_pages[url] = FetchError("unavailable")
    return source


def test_unreadable_catalog_blocks_publishing_instead_of_assuming_zero(tmp_path):
    output_path = tmp_path / "cards.json"
    output_path.write_text("{truncated", encoding="utf-8")

    with pytest.raises(CollectionError, match="cannot read"):
        collect_card_catalog(CardCollectionOptions(resume=False), _source(), tmp_path)

    assert output_path.read_text(encoding="utf-8") == "{truncated"


def test_catalog_floor_falls_back_to_the_checkpoint(tmp_path):
    checkpoint_path = tmp_path / "cards.checkpoint.json"
    checkpoint_path.write_text(
        json.dumps(
            [
                {"url": f"https://example.test/{index}", "name": "Complete"}
                for index in range(5)
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(CollectionError, match="refusing to shrink"):
        collect_card_catalog(CardCollectionOptions(resume=False), _source(), tmp_path)

    assert len(json.loads(checkpoint_path.read_text(encoding="utf-8"))) == 5
    assert not (tmp_path / "cards.json").exists()


def test_refusal_names_the_override_flag(tmp_path):
    (tmp_path / "cards.json").write_text(
        json.dumps([{"url": "https://example.test/0"}, {"url": "https://example.test/1"}]),
        encoding="utf-8",
    )

    with pytest.raises(CollectionError, match="--allow-shrink"):
        collect_card_catalog(CardCollectionOptions(resume=False), _source(), tmp_path)


def test_unreadable_checkpoint_does_not_block_a_fresh_rebuild(tmp_path):
    (tmp_path / "cards.checkpoint.json").write_text("{truncated", encoding="utf-8")
    messages = []

    result = collect_card_catalog(
        CardCollectionOptions(resume=False), _source(), tmp_path, log=messages.append
    )

    assert result.collected_count == 1
    assert len(json.loads((tmp_path / "cards.json").read_text(encoding="utf-8"))) == 1
    assert any("unreadable checkpoint" in message for message in messages)


def test_an_empty_result_is_never_published(tmp_path):
    with pytest.raises(CollectionError, match="refusing to publish an empty catalog"):
        collect_card_catalog(
            CardCollectionOptions(resume=False), _failing_source(), tmp_path
        )

    assert not (tmp_path / "cards.json").exists()
    assert not (tmp_path / "cards.checkpoint.json").exists()


def test_allow_shrink_publishes_a_smaller_catalog(tmp_path):
    output_path = tmp_path / "cards.json"
    output_path.write_text(
        json.dumps(
            [
                {"url": f"https://example.test/{index}", "name": "Complete"}
                for index in range(5)
            ]
        ),
        encoding="utf-8",
    )

    result = collect_card_catalog(
        CardCollectionOptions(resume=False, allow_shrink=True), _source(), tmp_path
    )

    assert result.collected_count == 1
    assert len(json.loads(output_path.read_text(encoding="utf-8"))) == 1
    assert not (tmp_path / "cards.fresh.checkpoint.json").exists()


def test_allow_shrink_does_not_license_an_empty_catalog(tmp_path):
    with pytest.raises(CollectionError, match="refusing to publish an empty catalog"):
        collect_card_catalog(
            CardCollectionOptions(resume=False, allow_shrink=True),
            _failing_source(),
            tmp_path,
        )


def test_interrupted_fresh_progress_is_marked_unresumable(tmp_path):
    source, _ = _two_card_source_interrupting_on_second()

    with pytest.raises(CollectionInterrupted) as excinfo:
        collect_card_catalog(CardCollectionOptions(resume=False), source, tmp_path)

    assert excinfo.value.resumable is False


def test_interrupted_resume_progress_is_marked_resumable(tmp_path):
    source, _ = _two_card_source_interrupting_on_second()

    with pytest.raises(CollectionInterrupted) as excinfo:
        collect_card_catalog(CardCollectionOptions(), source, tmp_path)

    assert excinfo.value.resumable is True

def test_refusal_persists_progress_so_a_rerun_need_not_refetch(tmp_path):
    (tmp_path / "cards.json").write_text(
        json.dumps(
            [
                {"url": f"https://example.test/{index}", "name": "Complete"}
                for index in range(3)
            ]
        ),
        encoding="utf-8",
    )
    url = "https://pocket.limitlesstcg.com/cards/A1/1"

    with pytest.raises(CollectionError, match="refusing to shrink"):
        collect_card_catalog(CardCollectionOptions(), _source(), tmp_path)

    checkpoint = json.loads(
        (tmp_path / "cards.checkpoint.json").read_text(encoding="utf-8")
    )
    assert [card["url"] for card in checkpoint] == [url]

    # A source that can no longer serve any page: the re-run must be satisfied
    # by the checkpoint alone, proving the refusal cost no repeated fetches.
    offline = InMemoryCardSource(
        sets=[{"set_id": "A1", "name": "Genetic Apex"}],
        card_urls={"A1": [url]},
        card_pages={},
    )
    result = collect_card_catalog(
        CardCollectionOptions(allow_shrink=True), offline, tmp_path
    )

    assert result.collected_count == 0
    assert result.skipped_count == 1
    assert len(json.loads((tmp_path / "cards.json").read_text(encoding="utf-8"))) == 1
