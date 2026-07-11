"""analysis.classify 的單元測試(純函式,合成牌表)。"""
from analysis.classify import classify_deck, deck_card_ids


def _decklist(*cards):
    """cards: (set, number) tuples -> decklist dict。"""
    return {"pokemon": [{"set": s, "number": n, "count": 1} for s, n in cards[:1]],
            "trainer": [{"set": s, "number": n, "count": 1} for s, n in cards[1:]]}


def test_deck_card_ids_extracts_set_number():
    dl = {"pokemon": [{"set": "A1", "number": "1", "count": 2}],
          "trainer": [{"set": "P-A", "number": "7", "count": 2}]}
    assert deck_card_ids(dl) == {"A1-1", "P-A-7"}


REFS = {
    "deckA": {"pokemon": [{"set": "A1", "number": str(i)} for i in (1, 2, 3)],
              "trainer": []},
    "deckB": {"pokemon": [{"set": "B1", "number": str(i)} for i in (1, 2)],
              "trainer": []},
}


def test_classify_exact_match():
    target = {"pokemon": [{"set": "A1", "number": str(i)} for i in (1, 2, 3)],
              "trainer": []}
    deck_id, sim = classify_deck(target, REFS)
    assert deck_id == "deckA"
    assert sim == 1.0


def test_classify_partial_match_picks_best():
    # 2/3 卡與 deckA 重疊 -> Jaccard 2/4 = 0.5;與 deckB 無重疊。
    target = {"pokemon": [{"set": "A1", "number": "1"},
                          {"set": "A1", "number": "2"},
                          {"set": "X9", "number": "9"}], "trainer": []}
    deck_id, sim = classify_deck(target, REFS)
    assert deck_id == "deckA"
    assert sim == 0.5


def test_classify_no_reference_returns_none():
    deck_id, sim = classify_deck(REFS["deckA"], {})
    assert deck_id is None
    assert sim == 0.0
