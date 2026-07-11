"""scraper.sets HTML 解析的單元測試(純函式,不涉及網路）。"""
from scraper.sets import parse_card_urls, parse_sets

INDEX_HTML = """
<table>
  <tr><th>Set</th><th>Date</th><th>Cards</th></tr>
  <tr>
    <td><a href="/cards/A1">Genetic Apex A1</a></td>
    <td>30 Oct 24</td><td>286</td>
  </tr>
  <tr>
    <td><a href="/cards/B3b">Everyday Wonders B3b</a></td>
    <td>30 Jun 26</td><td>106</td>
  </tr>
</table>
"""

SET_HTML = """
<div>
  <a href="/cards/A1/1">Bulbasaur</a>
  <a href="/cards/A1/1">Bulbasaur (dup link)</a>
  <a href="/cards/A1/2">Ivysaur</a>
  <a href="/cards/A2/1">Other set</a>
  <a href="/decks/A1">not a card</a>
</div>
"""


def test_parse_sets_extracts_id_name_count():
    sets = parse_sets(INDEX_HTML)
    assert sets[0] == {
        "set_id": "A1", "name": "Genetic Apex",
        "release_date": "30 Oct 24", "card_count": 286,
    }
    assert sets[1]["set_id"] == "B3b"
    assert sets[1]["name"] == "Everyday Wonders"
    assert sets[1]["card_count"] == 106


def test_parse_card_urls_filters_and_dedupes():
    urls = parse_card_urls(SET_HTML, "A1")
    assert urls == [
        "https://pocket.limitlesstcg.com/cards/A1/1",
        "https://pocket.limitlesstcg.com/cards/A1/2",
    ]
