"""FastAPI adapter that composes the runtime AnalysisEngine from artifacts."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from analysis.artifacts import load_engine
from analysis.model import ModelArtifactError
from analysis.runtime import AnalysisArtifactError, AnalysisEngine
from project_config import ANALYSIS_JSON, CARDS_JSON, MODEL_PATH


@lru_cache(maxsize=1)
def _load_default_engine() -> AnalysisEngine:
    return load_engine(
        ANALYSIS_JSON, cards_path=CARDS_JSON, model_path=MODEL_PATH
    )


def get_analysis_engine() -> AnalysisEngine:
    try:
        return _load_default_engine()
    except (AnalysisArtifactError, ModelArtifactError) as exc:
        raise HTTPException(
            status_code=503, detail=f"analysis unavailable: {exc}"
        ) from exc
