"""Versioned analysis and model artifact contracts."""

import pytest
import joblib
import json

from analysis.artifacts import load_engine, load_snapshot
from analysis.features import FEATURE_NAMES
from analysis.model import ModelArtifactError, WinModel
from analysis.runtime import AnalysisArtifactError, AnalysisSnapshot


def test_snapshot_rejects_unsupported_schema_version():
    with pytest.raises(AnalysisArtifactError, match="unsupported analysis schema version 2"):
        AnalysisSnapshot.from_dict(
            {
                "schema_version": 2,
                "generated_at": "2026-08-13T00:00:00+00:00",
                "source": {"tournaments": 0, "matches": 0,
                           "archetypes_total": 0, "archetypes_kept": 0},
                "archetypes": {},
                "matchups": {},
            }
        )


def test_snapshot_reports_missing_required_fields():
    with pytest.raises(AnalysisArtifactError, match="invalid analysis snapshot.*generated_at"):
        AnalysisSnapshot.from_dict(
            {
                "schema_version": 1,
                "source": {"tournaments": 0, "matches": 0,
                           "archetypes_total": 0, "archetypes_kept": 0},
                "archetypes": {},
                "matchups": {},
            }
        )


def test_snapshot_rejects_malformed_matchup_cell():
    with pytest.raises(AnalysisArtifactError, match="wins must be between 0 and games"):
        AnalysisSnapshot.from_dict(
            {
                "schema_version": 1,
                "generated_at": "2026-08-13T00:00:00+00:00",
                "source": {"tournaments": 1, "matches": 2,
                           "archetypes_total": 1, "archetypes_kept": 1},
                "archetypes": {},
                "matchups": {"A": {"B": {"wins": 3, "games": 2}}},
            }
        )


def test_missing_required_snapshot_file_is_explicit(tmp_path):
    path = tmp_path / "analysis.json"

    with pytest.raises(AnalysisArtifactError, match="analysis snapshot not found"):
        load_snapshot(path)


def test_model_rejects_incompatible_feature_schema(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(
        {
            "artifact_version": 1,
            "feature_schema": ["wrong-feature"],
            "pipe": object(),
            "features": {},
        },
        path,
    )

    with pytest.raises(ModelArtifactError, match="incompatible feature schema"):
        WinModel.load(path)


def test_engine_loads_without_optional_model_or_card_catalog(tmp_path):
    snapshot_path = tmp_path / "analysis.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-08-13T00:00:00+00:00",
                "source": {"tournaments": 0, "matches": 0,
                           "archetypes_total": 0, "archetypes_kept": 0},
                "archetypes": {},
                "matchups": {},
            }
        ),
        encoding="utf-8",
    )

    engine = load_engine(
        snapshot_path,
        cards_path=tmp_path / "missing-cards.json",
        model_path=tmp_path / "missing-model.joblib",
    )

    assert engine.meta().archetypes == ()
    assert engine.predict({"pokemon": [], "trainer": []}).ml_win_rate is None


def test_present_corrupt_model_is_an_operational_error(tmp_path):
    path = tmp_path / "model.joblib"
    path.write_bytes(b"not a joblib artifact")

    with pytest.raises(ModelArtifactError, match="invalid model artifact"):
        WinModel.load(path)


def test_snapshot_rejects_archetype_missing_required_share():
    with pytest.raises(AnalysisArtifactError, match="invalid analysis snapshot.*share"):
        AnalysisSnapshot.from_dict(
            {
                "schema_version": 1,
                "generated_at": "2026-08-13T00:00:00+00:00",
                "source": {"tournaments": 1, "matches": 0,
                           "archetypes_total": 1, "archetypes_kept": 1},
                "archetypes": {
                    "A": {"name": "A", "players": 1,
                          "overall": None, "decklist": {}}
                },
                "matchups": {},
            }
        )


def test_version_one_snapshot_round_trip_is_lossless():
    data = {
        "schema_version": 1,
        "generated_at": "2026-08-13T00:00:00+00:00",
        "source": {"tournaments": 0, "matches": 0,
                   "archetypes_total": 0, "archetypes_kept": 0},
        "archetypes": {},
        "matchups": {},
    }

    assert AnalysisSnapshot.from_dict(data).to_dict() == data


def test_model_rejects_unsupported_artifact_version(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(
        {"artifact_version": 2, "feature_schema": [],
         "pipe": object(), "features": {}},
        path,
    )

    with pytest.raises(ModelArtifactError, match="unsupported model artifact version 2"):
        WinModel.load(path)


def test_snapshot_rejects_invalid_generated_timestamp():
    with pytest.raises(AnalysisArtifactError, match="generated_at must be ISO-8601"):
        AnalysisSnapshot.from_dict(
            {
                "schema_version": 1,
                "generated_at": "not-a-time",
                "source": {"tournaments": 0, "matches": 0,
                           "archetypes_total": 0, "archetypes_kept": 0},
                "archetypes": {},
                "matchups": {},
            }
        )


def test_model_rejects_feature_vectors_with_wrong_length(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(
        {"artifact_version": 1, "feature_schema": list(FEATURE_NAMES),
         "pipe": object(), "features": {"deckA": [1.0]}},
        path,
    )

    with pytest.raises(ModelArtifactError, match="invalid model feature vector"):
        WinModel.load(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("archetypes", [], "archetypes must be an object"),
        ("source.matches", -1, "source counts must be non-negative integers"),
        ("archetypes.A.share", "half", "share must be between 0 and 1"),
    ],
)
def test_snapshot_rejects_invalid_required_field_types_and_ranges(
    field, value, message
):
    data = {
        "schema_version": 1,
        "generated_at": "2026-08-13T00:00:00+00:00",
        "source": {"tournaments": 1, "matches": 0,
                   "archetypes_total": 1, "archetypes_kept": 1},
        "archetypes": {
            "A": {"name": "A", "players": 1, "share": 0.5,
                  "overall": None, "decklist": {}}
        },
        "matchups": {},
    }
    target = data
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value

    with pytest.raises(AnalysisArtifactError, match=message):
        AnalysisSnapshot.from_dict(data)


def test_model_rejects_pipeline_without_prediction_contract(tmp_path):
    path = tmp_path / "model.joblib"
    joblib.dump(
        {"artifact_version": 1, "feature_schema": list(FEATURE_NAMES),
         "pipe": object(), "features": {}},
        path,
    )

    with pytest.raises(ModelArtifactError, match="invalid model prediction pipeline"):
        WinModel.load(path)
