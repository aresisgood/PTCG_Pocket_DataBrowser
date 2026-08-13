"""訓練勝率 ML 模型並與原型對戰表基準做誠實比較。

比較在同一組保留測試對戰上進行(預測 deck_a 是否擊敗 deck_b),並特別呈現
「基準沒看過的對戰」佔比與其上的表現——那正是 ML 相對查表的價值所在。
"""
from __future__ import annotations

import json
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from project_config import DATA_DIR, MODEL_PATH

from .features import build_card_index
from .matchups import matchup_table
from .model import archetype_features, train_model



def load_card_index() -> dict[str, dict[str, Any]]:
    cards = json.loads((DATA_DIR / "cards.json").read_text(encoding="utf-8"))
    return build_card_index(cards)


def _baseline_prob(table, a: str, b: str) -> tuple[float, bool]:
    """查表基準:回傳 (P(a勝), 是否有資料)。"""
    cell = table.get(a, {}).get(b)
    if cell and cell["games"] > 0:
        return cell["wins"] / cell["games"], True
    return 0.5, False


def train_and_evaluate(dataset: dict[str, Any],
                       card_index: dict[str, dict[str, Any]],
                       *, test_size: float = 0.2, seed: int = 42) -> dict[str, Any]:
    matches = dataset["matches"]
    decklists = dataset["decklists"]
    feats = archetype_features(decklists, card_index)

    train_m, test_m = train_test_split(matches, test_size=test_size,
                                       random_state=seed)
    model = train_model(train_m, decklists, card_index)
    table = matchup_table(train_m)

    y_true: list[int] = []
    ml_p: list[float] = []
    base_p: list[float] = []
    seen_mask: list[bool] = []
    for m in test_m:
        a, b, w = m["deck_a"], m["deck_b"], m["winner_deck"]
        if a not in feats or b not in feats:
            continue
        y_true.append(1 if w == a else 0)
        ml_p.append(model.win_prob(feats[a], feats[b]))
        p, seen = _baseline_prob(table, a, b)
        base_p.append(p)
        seen_mask.append(seen)

    y = np.array(y_true)
    ml = np.array(ml_p)
    base = np.array(base_p)
    seen = np.array(seen_mask)

    def metrics(p):
        return {
            "accuracy": accuracy_score(y, (p >= 0.5).astype(int)),
            "log_loss": log_loss(y, np.clip(p, 1e-6, 1 - 1e-6)),
            "auc": roc_auc_score(y, p) if len(set(y)) > 1 else float("nan"),
        }

    unseen = ~seen
    report = {
        "n_test": len(y),
        "unseen_frac": float(unseen.mean()) if len(y) else 0.0,
        "ml": metrics(ml),
        "baseline": metrics(base),
        "baseline_seen_only_acc": (
            accuracy_score(y[seen], (base[seen] >= 0.5).astype(int))
            if seen.any() else float("nan")),
        "ml_on_unseen_acc": (
            accuracy_score(y[unseen], (ml[unseen] >= 0.5).astype(int))
            if unseen.any() else float("nan")),
    }
    return {"model": model, "report": report}


def build_and_save(dataset: dict[str, Any],
                   card_index: dict[str, dict[str, Any]],
                   path=MODEL_PATH):
    """以全部對戰訓練正式模型並存檔(含各原型特徵）。"""
    model = train_model(dataset["matches"], dataset["decklists"], card_index)
    path.parent.mkdir(parents=True, exist_ok=True)
    model.save(path)
    return model


def main() -> None:
    """CLI:python -m analysis.train_ml — 評估、訓練並存檔模型。"""
    from project_config import TOURNAMENT_DATASET_JSON as DATASET_JSON

    dataset = json.loads(DATASET_JSON.read_text(encoding="utf-8"))
    card_index = load_card_index()

    r = train_and_evaluate(dataset, card_index)["report"]
    print(f"保留測試 {r['n_test']} 場,基準未見對戰佔比 {r['unseen_frac']*100:.1f}%")
    print(f"  ML       acc={r['ml']['accuracy']:.3f} "
          f"logloss={r['ml']['log_loss']:.3f} auc={r['ml']['auc']:.3f}")
    print(f"  查表基準 acc={r['baseline']['accuracy']:.3f} "
          f"logloss={r['baseline']['log_loss']:.3f} auc={r['baseline']['auc']:.3f}")
    print(f"  ML 在基準未見對戰上的準確率 {r['ml_on_unseen_acc']*100:.1f}% (基準只能猜 50%)")

    build_and_save(dataset, card_index)
    print(f"正式模型已存 -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
