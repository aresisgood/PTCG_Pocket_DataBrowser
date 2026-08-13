"""勝率分析套件。

模組:
    matchups - 由對戰紀錄計算原型對戰矩陣、整體勝率、Meta 佔比
    classify - 牌組 → 最近的已知原型（卡片重疊度）
    predict  - 綜合對戰表 + Meta 佔比 → 預估勝率 + 信心度
"""

from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from .build import build_analysis
    from .model import ModelArtifactError, train_model

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


def __getattr__(name: str) -> Any:
    """Lazily expose offline builder/trainer APIs without loading sklearn."""
    if name == "build_analysis":
        from .build import build_analysis
        return build_analysis
    if name in {"ModelArtifactError", "train_model"}:
        from .model import ModelArtifactError, train_model
        return {"ModelArtifactError": ModelArtifactError,
                "train_model": train_model}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
