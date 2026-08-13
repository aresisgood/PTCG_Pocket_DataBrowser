"""Analysis runtime behavior through the public AnalysisEngine seam."""

import pytest

from analysis.runtime import AnalysisEngine, AnalysisSnapshot, PredictionPolicy


def _snapshot() -> AnalysisSnapshot:
    return AnalysisSnapshot.from_dict(
        {
            "schema_version": 1,
            "generated_at": "2026-08-13T00:00:00+00:00",
            "source": {"tournaments": 2, "matches": 100,
                       "archetypes_total": 2, "archetypes_kept": 2},
            "archetypes": {
                "deckA": {
                    "name": "Deck A", "share": 0.6, "players": 30,
                    "overall": {"wins": 60, "games": 100, "rate": 0.6},
                    "decklist": {"pokemon": [
                        {"set": "A1", "number": str(i)} for i in (1, 2, 3)
                    ], "trainer": []},
                },
                "deckB": {
                    "name": "Deck B", "share": 0.4, "players": 20,
                    "overall": {"wins": 40, "games": 100, "rate": 0.4},
                    "decklist": {"pokemon": [
                        {"set": "B1", "number": str(i)} for i in (1, 2, 3)
                    ], "trainer": []},
                },
            },
            "matchups": {
                "deckA": {
                    "deckB": {"wins": 30, "games": 40},
                    "deckA": {"wins": 10, "games": 20},
                },
                "deckB": {"deckA": {"wins": 10, "games": 40}},
            },
        }
    )


def test_known_deck_prediction_and_meta_are_typed_and_complete():
    engine = AnalysisEngine(_snapshot())
    decklist = {"pokemon": [
        {"set": "A1", "number": str(i)} for i in (1, 2, 3)
    ], "trainer": []}

    prediction = engine.predict(decklist)
    meta = engine.meta()

    assert prediction.archetype.id == "deckA"
    assert prediction.similarity == 1.0
    assert round(prediction.win_rate, 4) == 0.6
    assert prediction.coverage == 1.0
    assert prediction.games == 60
    assert prediction.confidence == "low"
    assert prediction.best[0].name == "Deck B"
    assert [row.id for row in meta.archetypes] == ["deckA", "deckB"]
    assert meta.source.matches == 100


def test_unknown_deck_can_still_receive_ml_estimate():
    class Predictor:
        def __init__(self):
            self.received = None

        def predict(self, decklist, card_index, meta_share):
            self.received = decklist
            return 0.57

    predictor = Predictor()
    engine = AnalysisEngine(
        _snapshot(), predictor=predictor,
        card_index={"Z9-9": {"card_type": "pokemon"}},
    )
    unknown = {"pokemon": [{"set": "Z9", "number": "9"}], "trainer": []}

    prediction = engine.predict(unknown)

    assert prediction.archetype is None
    assert prediction.confidence == "unknown"
    assert prediction.ml_win_rate == 0.57
    assert prediction.best == prediction.worst == ()
    assert predictor.received is unknown


def test_missing_card_catalog_disables_ml_without_blocking_table_prediction():
    class Predictor:
        def predict(self, decklist, card_index, meta_share):
            raise AssertionError("predictor must not run without card catalog")

    engine = AnalysisEngine(_snapshot(), predictor=Predictor())
    known = _snapshot().archetypes["deckA"].decklist

    prediction = engine.predict(known)

    assert prediction.archetype.id == "deckA"
    assert prediction.win_rate is not None
    assert prediction.ml_win_rate is None


def test_flat_card_input_is_normalized_inside_engine():
    class Predictor:
        received = None

        def predict(self, decklist, card_index, meta_share):
            self.received = decklist
            return 0.5

    predictor = Predictor()
    engine = AnalysisEngine(
        _snapshot(),
        predictor=predictor,
        card_index={
            "A1-1": {"card_type": "pokemon"},
            "A1-2": {"card_type": "trainer"},
        },
    )

    engine.predict([
        {"set": "A1", "number": "1"},
        {"set": "A1", "number": "2"},
    ])

    assert predictor.received == {
        "pokemon": [{"set": "A1", "number": "1"}],
        "trainer": [{"set": "A1", "number": "2"}],
    }


def test_prediction_policy_controls_similarity_and_sample_thresholds():
    partial = {"pokemon": [
        {"set": "A1", "number": "1"},
        {"set": "A1", "number": "2"},
        {"set": "X", "number": "9"},
    ], "trainer": []}
    strict = AnalysisEngine(
        _snapshot(),
        policy=PredictionPolicy(similarity_threshold=0.6),
    )
    permissive = AnalysisEngine(
        _snapshot(),
        policy=PredictionPolicy(
            similarity_threshold=0.4, min_matchup_games=50
        ),
    )

    assert strict.predict(partial).archetype is None
    insufficient = permissive.predict(partial)
    assert insufficient.archetype.id == "deckA"
    assert insufficient.win_rate is None
    assert insufficient.games == 0
    assert insufficient.coverage == 0.0


def test_classification_ties_are_deterministic():
    data = _snapshot().to_dict()
    data["archetypes"]["deckB"]["decklist"] = data["archetypes"]["deckA"]["decklist"]
    engine = AnalysisEngine(AnalysisSnapshot.from_dict(data))

    prediction = engine.predict(data["archetypes"]["deckA"]["decklist"])

    assert prediction.archetype.id == "deckA"


def test_matchup_results_are_ordered_named_and_limited():
    data = _snapshot().to_dict()
    data["archetypes"]["deckA"]["share"] = 0.4
    data["matchups"]["deckA"] = {}
    for index, deck_id in enumerate(("C", "D", "E", "F", "G", "H"), start=1):
        data["archetypes"][deck_id] = {
            "name": f"Deck {deck_id}", "share": 0.1, "players": 1,
            "overall": None, "decklist": {},
        }
        data["matchups"]["deckA"][deck_id] = {
            "wins": index, "games": 10,
        }
    engine = AnalysisEngine(
        AnalysisSnapshot.from_dict(data),
        policy=PredictionPolicy(min_matchup_games=1, matchup_result_limit=2),
    )

    prediction = engine.predict(data["archetypes"]["deckA"]["decklist"])

    assert [(row.opponent, row.name) for row in prediction.best] == [
        ("H", "Deck H"), ("G", "Deck G")
    ]
    assert [row.opponent for row in prediction.worst] == ["C", "D"]


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (PredictionPolicy(high_confidence_games=50), "high"),
        (PredictionPolicy(medium_confidence_games=50,
                          medium_confidence_coverage=0.5), "medium"),
        (PredictionPolicy(), "low"),
    ],
)
def test_confidence_levels_follow_central_policy(policy, expected):
    engine = AnalysisEngine(_snapshot(), policy=policy)

    result = engine.predict(_snapshot().archetypes["deckA"].decklist)

    assert result.confidence == expected
