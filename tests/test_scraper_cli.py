"""CLI compatibility tests for collection option mapping."""

import sys

import pytest

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


def test_card_cli_reports_interrupt_as_clean_exit(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scraper"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)

    def interrupted(options, source, output):
        raise card_cli.CollectionInterrupted(7, output / "cards.fresh.checkpoint.json")

    monkeypatch.setattr(card_cli, "collect_card_catalog", interrupted)

    with pytest.raises(SystemExit) as excinfo:
        card_cli.main()

    assert excinfo.value.code == 130
    assert "cards.fresh.checkpoint.json" in capsys.readouterr().out

def test_card_cli_reports_an_interrupt_with_no_progress(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scraper"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)

    def interrupted(options, source, output):
        raise card_cli.CollectionInterrupted(0)

    monkeypatch.setattr(card_cli, "collect_card_catalog", interrupted)

    with pytest.raises(SystemExit) as excinfo:
        card_cli.main()

    assert excinfo.value.code == 130
    assert "權威檔案未被修改" in capsys.readouterr().out


def test_card_cli_reports_a_refused_publish_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scraper", "--set", "A1", "--no-resume"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)

    def refused(options, source, output):
        raise card_cli.CollectionError("refusing to shrink cards.json from 3900 to 1")

    monkeypatch.setattr(card_cli, "collect_card_catalog", refused)

    with pytest.raises(SystemExit) as excinfo:
        card_cli.main()

    assert excinfo.value.code == 1
    assert "refusing to shrink" in capsys.readouterr().out

def test_card_cli_reports_a_bare_interrupt_as_clean_exit(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scraper"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)

    def interrupted(options, source, output):
        raise KeyboardInterrupt()

    monkeypatch.setattr(card_cli, "collect_card_catalog", interrupted)

    with pytest.raises(SystemExit) as excinfo:
        card_cli.main()

    assert excinfo.value.code == 130
    assert "已中斷" in capsys.readouterr().out

def test_card_cli_passes_the_allow_shrink_flag_through(monkeypatch):
    captured = {}
    monkeypatch.setattr(sys, "argv", ["scraper", "--allow-shrink"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)
    monkeypatch.setattr(
        card_cli,
        "collect_card_catalog",
        lambda options, source, output: captured.update(options=options),
    )

    card_cli.main()

    assert captured["options"].allow_shrink is True


def test_card_cli_does_not_claim_artifacts_are_untouched_on_a_late_interrupt(
    monkeypatch, capsys
):
    monkeypatch.setattr(sys, "argv", ["scraper"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)

    def interrupted(options, source, output):
        raise KeyboardInterrupt()

    monkeypatch.setattr(card_cli, "collect_card_catalog", interrupted)

    with pytest.raises(SystemExit) as excinfo:
        card_cli.main()

    output = capsys.readouterr().out
    assert excinfo.value.code == 130
    assert "沒有任何檔案被修改" not in output
    assert "data/cards.json" in output

def test_card_cli_tells_a_resumable_interrupt_apart(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scraper"])
    monkeypatch.setattr(card_cli, "HttpCardSource", ContextSource)

    def interrupted(options, source, output):
        raise card_cli.CollectionInterrupted(
            7, output / "cards.checkpoint.json", resumable=True
        )

    monkeypatch.setattr(card_cli, "collect_card_catalog", interrupted)

    with pytest.raises(SystemExit) as excinfo:
        card_cli.main()

    output = capsys.readouterr().out
    assert excinfo.value.code == 130
    assert "重新執行即可續爬" in output
    assert "不會自動續用" not in output
