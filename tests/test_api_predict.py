"""預測與 Meta 端點的整合測試(注入合成分析資料）。"""
import pytest
from fastapi.testclient import TestClient
from api.analysis_store import AnalysisStore, get_store
from api.main import create_app

ANALYSIS = {
    "archetypes": {
        "deckA": {"name": "Deck A", "share": 0.6, "players": 30,
                  "overall": {"wins": 60, "games": 100, "rate": 0.6},
                  "decklist": {"pokemon": [{"set": "A1", "number": str(i)}
                                           for i in (1, 2, 3)], "trainer": []}},
        "deckB": {"name": "Deck B", "share": 0.4, "players": 20,
                  "overall": {"wins": 40, "games": 100, "rate": 0.4},
                  "decklist": {"pokemon": [{"set": "B1", "number": str(i)}
                                           for i in (1, 2, 3)], "trainer": []}},
    },
    "matchups": {
        "deckA": {"deckB": {"wins": 30, "games": 40},
                  "deckA": {"wins": 10, "games": 20}},
        "deckB": {"deckA": {"wins": 10, "games": 40}},
    },
    "source": {"tournaments": 40, "matches": 100},
}


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    app.dependency_overrides[get_store] = lambda: AnalysisStore(ANALYSIS)
    with TestClient(app) as c:
        yield c


def test_predict_known_deck(client):
    cards = [{"set": "A1", "number": str(i)} for i in (1, 2, 3)]
    r = client.post("/api/predict", json={"cards": cards})
    assert r.status_code == 200
    body = r.json()
    assert body["archetype"]["id"] == "deckA"
    assert body["similarity"] == 1.0
    # (0.75*0.4 + 0.5*0.6) / (0.4+0.6) = 0.6
    assert round(body["win_rate"], 4) == 0.6
    assert body["best"][0]["opponent"] == "deckB"       # 最有利
    assert body["best"][0]["name"] == "Deck B"          # 名稱有補上


def test_predict_unknown_deck(client):
    cards = [{"set": "Z9", "number": "9"}]
    r = client.post("/api/predict", json={"cards": cards})
    body = r.json()
    assert body["archetype"] is None
    assert body["win_rate"] is None
    assert body["confidence"] == "unknown"


def test_meta_sorted_by_share(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    rows = r.json()["archetypes"]
    assert [x["id"] for x in rows] == ["deckA", "deckB"]
    assert rows[0]["win_rate"] == 0.6


# --- ML 路徑(注入真的訓練好的模型)-----------------------------------------

_ML_CARDS = {
    "P-1": {"card_type": "pokemon", "element": "Fire", "hp": 200, "stage": "Basic",
            "ability_name": "A", "retreat_cost": 1, "name": "Strong ex"},
    "P-2": {"card_type": "pokemon", "element": "Grass", "hp": 50, "stage": "Basic",
            "ability_name": "", "retreat_cost": 3, "name": "Weak"},
}
_ML_DECKS = {
    "strong": {"pokemon": [{"set": "P", "number": "1", "count": 2}], "trainer": []},
    "weak": {"pokemon": [{"set": "P", "number": "2", "count": 2}], "trainer": []},
}


@pytest.fixture
def ml_client(tmp_path):
    from analysis.model import train_model
    model = train_model([{"deck_a": "strong", "deck_b": "weak",
                          "winner_deck": "strong"}] * 20, _ML_DECKS, _ML_CARDS)
    data = {"archetypes": {
        "strong": {"name": "Strong", "share": 0.5, "decklist": _ML_DECKS["strong"]},
        "weak": {"name": "Weak", "share": 0.5, "decklist": _ML_DECKS["weak"]},
    }, "matchups": {}, "source": {}}
    store = AnalysisStore(data, card_index=_ML_CARDS, model=model)
    app = create_app(f"sqlite:///{tmp_path / 'ml.db'}")
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as c:
        yield c


def test_predict_returns_ml_estimate(ml_client):
    cards = [{"set": "P", "number": "1", "count": 2}]  # 強牌
    r = ml_client.post("/api/predict", json={"cards": cards}).json()
    assert r["ml_win_rate"] is not None
    assert r["ml_win_rate"] > 0.5   # 強牌對 Meta 應 >50%


def test_predict_rejects_empty_card_list(client):
    response = client.post("/api/predict", json={"cards": []})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "card",
    [
        {"set": "", "number": "1", "count": 1},
        {"set": "A1", "number": "", "count": 1},
        {"set": "A1", "number": "1", "count": 0},
        {"set": "A1", "number": "1", "count": 3},
    ],
)
def test_predict_rejects_invalid_card(client, card):
    response = client.post("/api/predict", json={"cards": [card]})
    assert response.status_code == 422
