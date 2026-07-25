from fastapi.testclient import TestClient

from api.main import create_app


def test_cards_data_is_public_but_database_file_is_not_served(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "cards.json").write_text('[{"name": "Pikachu"}]', encoding="utf-8")
    (data_dir / "decks.db").write_bytes(b"SQLite format 3\x00private-state")
    monkeypatch.setattr("api.main.DATA_DIR", data_dir)

    app = create_app(f"sqlite:///{tmp_path / 'application.db'}")
    with TestClient(app) as client:
        cards_response = client.get("/data/cards.json")
        database_response = client.get("/data/decks.db")

    assert cards_response.status_code == 200
    assert cards_response.json() == [{"name": "Pikachu"}]
    assert database_response.status_code == 404
