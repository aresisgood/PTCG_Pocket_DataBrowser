"""Thin HTTP adapters for deck prediction and Meta retrieval."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from analysis.runtime import AnalysisEngine, Prediction

from ..analysis_provider import get_analysis_engine
from ..schemas import PredictRequest

router = APIRouter(prefix="/api", tags=["predict"])


@router.post("/predict")
def predict(
    req: PredictRequest,
    engine: AnalysisEngine = Depends(get_analysis_engine),
):
    result = engine.predict(
        [card.model_dump(exclude_none=True) for card in req.cards]
    )
    return _prediction_response(result)


@router.get("/meta")
def meta(engine: AnalysisEngine = Depends(get_analysis_engine)):
    result = engine.meta()
    return {
        "source": asdict(result.source),
        "archetypes": [asdict(row) for row in result.archetypes],
    }


def _prediction_response(result: Prediction) -> dict:
    response = {
        "archetype": asdict(result.archetype) if result.archetype else None,
        "similarity": result.similarity,
        "win_rate": result.win_rate,
        "ml_win_rate": result.ml_win_rate,
        "confidence": result.confidence,
        "best": [asdict(row) for row in result.best],
        "worst": [asdict(row) for row in result.worst],
    }
    if result.archetype is None:
        response["message"] = result.message
    else:
        response["coverage"] = result.coverage
        response["games"] = result.games
    return response
