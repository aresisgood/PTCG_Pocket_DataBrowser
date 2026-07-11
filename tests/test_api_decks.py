"""牌組 CRUD API 的整合測試(FastAPI TestClient + 暫存 SQLite）。"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine

from api import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    # 把資料庫換成暫存檔,測試互不干擾、也不碰真實 decks.db。
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(db, "engine", test_engine)
    from api.main import create_app
    with TestClient(create_app()) as c:  # 進入時觸發 lifespan -> init_db
        yield c


SAMPLE = {
    "name": "My Miraidon",
    "cards": [{"set": "B3a", "number": "1", "name": "Miraidon ex", "count": 2}],
}


def test_create_and_get_deck(client):
    r = client.post("/api/decks", json=SAMPLE)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] >= 1
    assert body["name"] == "My Miraidon"
    assert body["cards"][0]["name"] == "Miraidon ex"

    got = client.get(f"/api/decks/{body['id']}")
    assert got.status_code == 200
    assert got.json()["name"] == "My Miraidon"


def test_list_decks(client):
    client.post("/api/decks", json=SAMPLE)
    client.post("/api/decks", json={"name": "Other", "cards": []})
    r = client.get("/api/decks")
    assert r.status_code == 200
    assert {d["name"] for d in r.json()} == {"My Miraidon", "Other"}


def test_update_deck(client):
    deck_id = client.post("/api/decks", json=SAMPLE).json()["id"]
    r = client.put(f"/api/decks/{deck_id}",
                   json={"name": "Renamed", "cards": []})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"
    assert r.json()["cards"] == []


def test_delete_deck(client):
    deck_id = client.post("/api/decks", json=SAMPLE).json()["id"]
    assert client.delete(f"/api/decks/{deck_id}").status_code == 204
    assert client.get(f"/api/decks/{deck_id}").status_code == 404


def test_get_missing_deck_returns_404(client):
    assert client.get("/api/decks/999").status_code == 404
