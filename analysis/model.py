"""以牌組特徵預測勝率的 ML 模型(scikit-learn 邏輯迴歸）。

訓練資料:每場對戰取「A 特徵 − B 特徵」為輸入、A 是否獲勝為標籤,並同時
加入相反向量與相反標籤,使模型天然滿足反對稱(P(A勝B)+P(B勝A)=1)。

相對於原型對戰表(僅能查已見過的對戰),此模型以牌組「內容」預測,能推廣到
稀有對戰與自製牌組。
"""
from __future__ import annotations

from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import feature_vector


def archetype_features(decklists: dict[str, Any],
                       card_index: dict[str, dict[str, Any]]) -> dict[str, list[float]]:
    """每個原型代表牌表的特徵向量。"""
    return {aid: feature_vector(dl, card_index) for aid, dl in decklists.items()}


def build_training_data(matches: list[dict[str, Any]],
                        features: dict[str, list[float]]):
    """由對戰產生 (X, y);每場對戰加入正反兩筆以確保反對稱。"""
    X: list[np.ndarray] = []
    y: list[int] = []
    for m in matches:
        a, b, winner = m["deck_a"], m["deck_b"], m["winner_deck"]
        if a not in features or b not in features:
            continue
        diff = np.array(features[a]) - np.array(features[b])
        label = 1 if winner == a else 0
        X.append(diff)
        y.append(label)
        X.append(-diff)
        y.append(1 - label)
    return np.array(X), np.array(y)


class WinModel:
    """訓練好的勝率模型 + 各原型特徵,提供預測介面。"""

    def __init__(self, pipe: Pipeline, features: dict[str, list[float]] | None = None):
        self.pipe = pipe
        self.features = features or {}

    def win_prob(self, feat_a: list[float], feat_b: list[float]) -> float:
        """P(A 擊敗 B)。"""
        diff = (np.array(feat_a) - np.array(feat_b)).reshape(1, -1)
        return float(self.pipe.predict_proba(diff)[0, 1])

    def deck_win_rate(self, deck_feat: list[float],
                      meta_features: dict[str, list[float]],
                      meta_share: dict[str, float]) -> float | None:
        """對當前 Meta 各原型加權平均的預估勝率。"""
        num = den = 0.0
        for opp, share in meta_share.items():
            if opp not in meta_features:
                continue
            num += self.win_prob(deck_feat, meta_features[opp]) * share
            den += share
        return num / den if den else None

    def save(self, path) -> None:
        joblib.dump({"pipe": self.pipe, "features": self.features}, path)

    @classmethod
    def load(cls, path) -> "WinModel":
        blob = joblib.load(path)
        return cls(blob["pipe"], blob.get("features", {}))


def train_model(matches: list[dict[str, Any]],
                decklists: dict[str, Any],
                card_index: dict[str, dict[str, Any]]) -> WinModel:
    """訓練並回傳 WinModel。"""
    features = archetype_features(decklists, card_index)
    X, y = build_training_data(matches, features)
    pipe = make_pipeline(StandardScaler(),
                         LogisticRegression(max_iter=1000))
    pipe.fit(X, y)
    return WinModel(pipe, features)
