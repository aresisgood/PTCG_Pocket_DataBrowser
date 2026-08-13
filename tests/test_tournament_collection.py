"""Tournament dataset collection through its public workflow seam."""

from scraper.fetch import FetchError
from scraper.tournament_dataset import (
    HttpTournamentSource,
    InMemoryTournamentSource,
    TournamentCollectionOptions,
    collect_tournament_dataset,
)


class FailingTournamentSource(InMemoryTournamentSource):
    def get_standings(self, tournament_id):
        if tournament_id == "bad":
            raise FetchError("upstream unavailable")
        return super().get_standings(tournament_id)


def test_unknown_winner_is_skipped_and_reported(tmp_path):
    source = InMemoryTournamentSource(
        tournaments=[
            {"id": "t1", "name": "Cup", "date": "2026-08-01", "players": 2}
        ],
        standings={
            "t1": [
                {"player": "a", "deck": {"id": "deck-a", "name": "A"}},
                {"player": "b", "deck": {"id": "deck-b", "name": "B"}},
            ]
        },
        pairings={
            "t1": [{"player1": "a", "player2": "b", "winner": "missing"}]
        },
    )

    result = collect_tournament_dataset(
        TournamentCollectionOptions(min_players=0), source, tmp_path
    )

    assert result.collected_count == 1
    assert result.summary.dataset["matches"] == []
    assert set(result.summary.dataset) == {
        "matches", "meta", "names", "decklists", "tournaments"
    }
    assert result.warnings == [
        "tournament t1: skipped pairing with unknown winner 'missing'"
    ]


def test_failed_tournament_is_excluded_from_provenance_and_reported(tmp_path):
    source = FailingTournamentSource(
        tournaments=[
            {"id": "good", "name": "Good", "date": "2026-08-01", "players": 2},
            {"id": "bad", "name": "Bad", "date": "2026-08-02", "players": 2},
        ],
        standings={"good": []},
        pairings={"good": []},
    )

    result = collect_tournament_dataset(
        TournamentCollectionOptions(min_players=0), source, tmp_path
    )

    assert [item["id"] for item in result.summary.dataset["tournaments"]] == [
        "good"
    ]
    assert result.collected_count == 1
    assert result.skipped_count == 0
    assert result.failures[0].item_id == "bad"
    assert result.summary.selected_tournaments == 2
    assert result.summary.successful_tournament_ids == ["good"]
    assert result.summary.failed_tournament_ids == ["bad"]


def test_tournament_http_source_closes_only_an_internally_created_session(monkeypatch):
    class TrackingSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    created = TrackingSession()
    monkeypatch.setattr("scraper.tournament_dataset.requests.Session", lambda: created)

    internal = HttpTournamentSource(delay=0)
    internal.close()
    assert created.closed is True

    supplied = TrackingSession()
    external = HttpTournamentSource(session=supplied, delay=0)
    external.close()
    assert supplied.closed is False
