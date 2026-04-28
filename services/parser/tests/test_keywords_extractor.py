from __future__ import annotations

import json

from card_reader_core.models import Keyword
from card_reader_parser.extractors.keywords_extractor import KeywordsExtractor


def test_extract_keyword_ids_matches_label_case_insensitively() -> None:
    extractor = KeywordsExtractor()
    keyword = Keyword(id="keyword-1", key="turn-start", label="Turn Start", identifiers_json='["turn start"]')

    matched = extractor.extract_keyword_ids("At TURN START, draw a card.", [keyword])

    assert matched == ["keyword-1"]


def test_extract_keyword_ids_matches_identifiers_case_insensitively() -> None:
    extractor = KeywordsExtractor()
    keyword = Keyword(
        id="keyword-1",
        key="turn-start",
        label="Turn Start",
        identifiers_json=json.dumps(["turn start", "at the beginning of your turn"]),
    )

    matched = extractor.extract_keyword_ids("AT THE BEGINNING OF YOUR TURN, draw a card.", [keyword])

    assert matched == ["keyword-1"]
