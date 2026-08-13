"""analysis.model 的單元測試(可分離的合成資料,結果方向可預期)。"""
import numpy as np

from analysis.model import build_training_data, train_model

# 強牌:EX、高 HP;弱牌:普通、低 HP。
CARD_INDEX = {
    "P-1": {"card_type": "pokemon", "element": "Fire", "hp": 200,
            "stage": "Basic", "ability_name": "A", "retreat_cost": 1,
            "name": "Strong ex"},
    "P-2": {"card_type": "pokemon", "element": "Grass", "hp": 50,
            "stage": "Basic", "ability_name": "", "retreat_cost": 3,
            "name": "Weak"},
}
DECKLISTS = {
    "strong": {"pokemon": [{"set": "P", "number": "1", "count": 2}], "trainer": []},
    "weak": {"pokemon": [{"set": "P", "number": "2", "count": 2}], "trainer": []},
}
# 強牌穩定擊敗弱牌。
MATCHES = [{"deck_a": "strong", "deck_b": "weak", "winner_deck": "strong"}] * 20


def test_build_training_data_is_antisymmetric():
    from analysis.model import archetype_features
    feats = archetype_features(DECKLISTS, CARD_INDEX)
    X, y = build_training_data(MATCHES, feats)
    assert len(X) == len(y) == 40             # 每場對戰產生正反兩筆
    # 反對稱:每筆都有一筆相反向量、相反標籤
    assert np.allclose(X[0], -X[1])
    assert y[0] + y[1] == 1


def test_model_learns_stronger_deck_wins():
    model = train_model(MATCHES, DECKLISTS, CARD_INDEX)
    p_strong = model.win_prob(model.features["strong"], model.features["weak"])
    p_weak = model.win_prob(model.features["weak"], model.features["strong"])
    assert p_strong > 0.6
    assert p_weak < 0.4
    assert round(p_strong + p_weak, 5) == 1.0  # 反對稱


def test_deck_win_rate_weights_by_meta():
    model = train_model(MATCHES, DECKLISTS, CARD_INDEX)
    meta_feats = model.features
    rate = model.deck_win_rate(model.features["strong"], meta_feats,
                               {"weak": 1.0})
    assert rate > 0.6


def test_predictor_accepts_decklist_and_hides_feature_vector():
    model = train_model(MATCHES, DECKLISTS, CARD_INDEX)

    rate = model.predict(DECKLISTS["strong"], CARD_INDEX, {"weak": 1.0})

    assert rate > 0.6


def test_versioned_model_save_load_round_trip(tmp_path):
    path = tmp_path / "model.joblib"
    model = train_model(MATCHES, DECKLISTS, CARD_INDEX)
    model.save(path)

    loaded = type(model).load(path)

    assert loaded.predict(DECKLISTS["strong"], CARD_INDEX, {"weak": 1.0}) > 0.6
