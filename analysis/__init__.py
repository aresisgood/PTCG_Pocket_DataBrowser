"""勝率分析套件。

模組:
    matchups - 由對戰紀錄計算原型對戰矩陣、整體勝率、Meta 佔比
    classify - 牌組 → 最近的已知原型（卡片重疊度）
    predict  - 綜合對戰表 + Meta 佔比 → 預估勝率 + 信心度
"""

from .artifacts import load_engine, load_snapshot
from .build import build_analysis, build_from_file
from .model import ModelArtifactError, WinModel, train_model
from .runtime import (
    AnalysisArtifactError,
    AnalysisEngine,
    AnalysisSnapshot,
    ArchetypeIdentity,
    MatchupSummary,
    MetaArchetype,
    MetaSnapshot,
    Prediction,
    PredictionPolicy,
)
from .train_ml import build_and_save, train_and_evaluate

__all__ = [
    "AnalysisArtifactError",
    "AnalysisEngine",
    "AnalysisSnapshot",
    "ArchetypeIdentity",
    "MatchupSummary",
    "MetaArchetype",
    "MetaSnapshot",
    "ModelArtifactError",
    "Prediction",
    "PredictionPolicy",
    "WinModel",
    "build_analysis",
    "build_and_save",
    "build_from_file",
    "load_engine",
    "load_snapshot",
    "train_and_evaluate",
    "train_model",
]
