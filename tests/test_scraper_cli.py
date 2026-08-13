"""CLI compatibility tests for collection option mapping."""

import sys

from scraper import __main__ as card_cli
from scraper import tournaments as tournament_cli


class ContextSource:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def test_card_cli_preserves_existing_options(monkeypatch):
    captured = {}
    monkeypatch.setattr(sys, "argv", ["scraper", "--test", "--set", "A1", "--no-resume"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)
    monkeypatch.setattr(
        card_cli,
        "collect_card_catalog",
        lambda options, source, output: captured.update(options=options, output=output),
    )

    card_cli.main()

    assert captured["options"].test_mode is True
    assert captured["options"].only_set == "A1"
    assert captured["options"].resume is False


def test_tournament_cli_preserves_existing_options(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        sys,
        "argv",
        ["tournaments", "--min-players", "64", "--after", "2026-01-01", "--max", "7"],
    )
    monkeypatch.setattr(
        "scraper.tournament_dataset.HttpTournamentSource", ContextSource
    )
    monkeypatch.setattr(
        "scraper.tournament_dataset.collect_tournament_dataset",
        lambda options, source, output: captured.update(options=options, output=output),
    )

    tournament_cli.main()

    assert captured["options"].min_players == 64
    assert captured["options"].after == "2026-01-01"
    assert captured["options"].max_tournaments == 7
