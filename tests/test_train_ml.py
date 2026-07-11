"""analysis.train_ml 評估流程的單元測試(小型合成資料集)。"""
import math

from analysis.train_ml import train_and_evaluate

CARD_INDEX = {
    "P-1": {"card_type": "pokemon", "element": "Fire", "hp": 200, "stage": "Basic",
            "ability_name": "A", "retreat_cost": 1, "name": "Strong ex"},
    "P-2": {"card_type": "pokemon", "element": "Grass", "hp": 50, "stage": "Basic",
            "ability_name": "", "retreat_cost": 3, "name": "Weak"},
}
DECKLISTS = {
    "strong": {"pokemon": [{"set": "P", "number": "1", "count": 2}], "trainer": []},
    "weak": {"pokemon": [{"set": "P", "number": "2", "count": 2}], "trainer": []},
}
# 兩種對戰方向皆有(讓測試集含兩個類別),強牌大多獲勝。
MATCHES = (
    [{"deck_a": "strong", "deck_b": "weak", "winner_deck": "strong"}] * 20 +
    [{"deck_a": "weak", "deck_b": "strong", "winner_deck": "strong"}] * 20
)


def test_train_and_evaluate_reports_metrics():
    out = train_and_evaluate({"matches": MATCHES, "decklists": DECKLISTS},
                             CARD_INDEX, test_size=0.3, seed=0)
    r = out["report"]
    assert r["n_test"] > 0
    for key in ("ml", "baseline"):
        assert 0.0 <= r[key]["accuracy"] <= 1.0
        assert r[key]["log_loss"] >= 0.0
    assert 0.0 <= r["unseen_frac"] <= 1.0
    # 強牌穩定獲勝,ML 至少不比亂猜差。
    assert r["ml"]["accuracy"] >= 0.5 or math.isnan(r["ml"]["auc"])
