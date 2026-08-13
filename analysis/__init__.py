"""勝率分析套件。

模組:
    matchups - 由對戰紀錄計算原型對戰矩陣、整體勝率、Meta 佔比
    classify - 牌組 → 最近的已知原型（卡片重疊度）
    predict  - 綜合對戰表 + Meta 佔比 → 預估勝率 + 信心度
"""

from .build import build_analysis
from .model import ModelArtifactError, train_model
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
    "build_analysis",
    "train_model",
]
