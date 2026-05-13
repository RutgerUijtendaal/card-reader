from __future__ import annotations

from card_reader_core.models import Symbol
from card_reader_parser.parsers.rule_text import RuleTextEnricher
from card_reader_parser.parsers.symbol_detector import DetectedSymbol, DetectionBBox


def test_rule_text_enricher_replaces_known_ocr_aliases_for_detected_symbols() -> None:
    symbol = Symbol(
        id="symbol-1",
        key="exhaust",
        label="Exhaust",
        symbol_type="misc",
        text_token="{EXHAUST}",
        text_enrichment_json={"ocr_aliases": ["Exbaust"]},
    )
    result = RuleTextEnricher().enrich(
        raw_text="Exbaust target unit.",
        detected_symbols=[
            DetectedSymbol(
                symbol_id="symbol-1",
                key="exhaust",
                symbol_type="misc",
                confidence=0.92,
                bbox=DetectionBBox(x=4, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            )
        ],
        symbols=[symbol],
    )

    assert result.cleaned_text == "Exbaust target unit."
    assert result.enriched_text == "[[symbol:exhaust]] target unit."
    assert result.rendered_text == "{EXHAUST} target unit."


def test_rule_text_enricher_can_replace_only_a_captured_part_of_ocr_alias_match() -> None:
    symbol = Symbol(
        id="symbol-1",
        key="fire-mana",
        label="Fire Mana",
        symbol_type="mana",
        text_token="{FM}",
        text_enrichment_json={
            "ocr_aliases": [
                {
                    "match_regex": r"(X)(,)",
                    "replace_group": 1,
                }
            ]
        },
    )
    result = RuleTextEnricher().enrich(
        raw_text="Gain X, then draw a card.",
        detected_symbols=[
            DetectedSymbol(
                symbol_id="symbol-1",
                key="fire-mana",
                symbol_type="mana",
                confidence=0.92,
                bbox=DetectionBBox(x=4, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            )
        ],
        symbols=[symbol],
    )

    assert result.cleaned_text == "Gain X, then draw a card."
    assert result.enriched_text == "Gain [[symbol:fire-mana]], then draw a card."
    assert result.rendered_text == "Gain {FM}, then draw a card."


def test_rule_text_enricher_ocr_alias_can_add_spacing_around_replaced_group() -> None:
    symbol = Symbol(
        id="symbol-1",
        key="fire-mana",
        label="Fire Mana",
        symbol_type="mana",
        text_token="{FM}",
        text_enrichment_json={
            "ocr_aliases": [
                {
                    "match_regex": r"(Gain)(X)(\.)",
                    "replace_group": 2,
                    "before_text": " ",
                    "after_text": "",
                }
            ]
        },
    )
    result = RuleTextEnricher().enrich(
        raw_text="GainX.",
        detected_symbols=[
            DetectedSymbol(
                symbol_id="symbol-1",
                key="fire-mana",
                symbol_type="mana",
                confidence=0.92,
                bbox=DetectionBBox(x=4, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            )
        ],
        symbols=[symbol],
    )

    assert result.cleaned_text == "GainX."
    assert result.enriched_text == "Gain [[symbol:fire-mana]]."
    assert result.rendered_text == "Gain {FM}."


def test_rule_text_enricher_inserts_placeholder_from_anchor_pattern() -> None:
    symbol = Symbol(
        id="symbol-1",
        key="exhaust",
        label="Exhaust",
        symbol_type="misc",
        text_token="{EXHAUST}",
        text_enrichment_json={"pattern_anchors": [{"match": ": ", "position": "before"}]},
    )
    result = RuleTextEnricher().enrich(
        raw_text=": Draw a card.",
        detected_symbols=[
            DetectedSymbol(
                symbol_id="symbol-1",
                key="exhaust",
                symbol_type="misc",
                confidence=0.93,
                bbox=DetectionBBox(x=4, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            )
        ],
        symbols=[symbol],
    )

    assert result.cleaned_text == ": Draw a card."
    assert result.enriched_text == "[[symbol:exhaust]]: Draw a card."
    assert result.rendered_text == "{EXHAUST}: Draw a card."


def test_rule_text_enricher_can_insert_spacing_around_anchor_matches() -> None:
    symbol = Symbol(
        id="symbol-1",
        key="fire-mana",
        label="Fire Mana",
        symbol_type="mana",
        text_token="{FM}",
        text_enrichment_json={
            "pattern_anchors": [
                {
                    "match": "Gain",
                    "position": "after",
                    "before_text": " ",
                    "after_text": " ",
                }
            ]
        },
    )
    result = RuleTextEnricher().enrich(
        raw_text="Gain 2 life.",
        detected_symbols=[
            DetectedSymbol(
                symbol_id="symbol-1",
                key="fire-mana",
                symbol_type="mana",
                confidence=0.93,
                bbox=DetectionBBox(x=4, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            )
        ],
        symbols=[symbol],
    )

    assert result.cleaned_text == "Gain 2 life."
    assert result.enriched_text == "Gain [[symbol:fire-mana]] 2 life."
    assert result.rendered_text == "Gain {FM} 2 life."


def test_rule_text_enricher_supports_regex_anchors_against_mutated_text() -> None:
    divine_symbol = Symbol(
        id="symbol-1",
        key="divine-mana",
        label="Divine Mana",
        symbol_type="mana",
        text_token="{DM}",
        text_enrichment_json={
            "pattern_anchors": [
                {
                    "match_regex": r"Gain(?!\s+\[\[symbol:)",
                    "position": "after",
                    "before_text": " ",
                    "after_text": " ",
                }
            ]
        },
    )
    martial_symbol = Symbol(
        id="symbol-2",
        key="martial-mana",
        label="Martial Mana",
        symbol_type="mana",
        text_token="{MM}",
        text_enrichment_json={
            "pattern_anchors": [
                {
                    "match_regex": r"\bor\b(?!\s+\[\[symbol:)",
                    "position": "after",
                    "before_text": " ",
                    "after_text": " ",
                }
            ]
        },
    )

    result = RuleTextEnricher().enrich(
        raw_text="[E]: Gain or",
        detected_symbols=[
            DetectedSymbol(
                symbol_id="symbol-1",
                key="divine-mana",
                symbol_type="mana",
                confidence=0.95,
                bbox=DetectionBBox(x=20, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            ),
            DetectedSymbol(
                symbol_id="symbol-2",
                key="martial-mana",
                symbol_type="mana",
                confidence=0.94,
                bbox=DetectionBBox(x=40, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            ),
        ],
        symbols=[divine_symbol, martial_symbol],
    )

    assert result.enriched_text == "[E]: Gain [[symbol:divine-mana]] or [[symbol:martial-mana]]"
    assert result.rendered_text == "[E]: Gain {DM} or {MM}"


def test_rule_text_enricher_regex_before_anchor_advances_past_existing_placeholder() -> None:
    symbol = Symbol(
        id="symbol-1",
        key="exhaust",
        label="Exhaust",
        symbol_type="generic",
        text_token="{E}",
        text_enrichment_json={
            "pattern_anchors": [
                {
                    "match_regex": r"(?m)^:\s",
                    "position": "before",
                }
            ]
        },
    )

    result = RuleTextEnricher().enrich(
        raw_text=": Gain\n: Draw",
        detected_symbols=[
            DetectedSymbol(
                symbol_id="symbol-1",
                key="exhaust",
                symbol_type="generic",
                confidence=0.95,
                bbox=DetectionBBox(x=5, y=5, w=8, h=8),
                detector_type="template",
                match_metadata={},
            ),
            DetectedSymbol(
                symbol_id="symbol-1",
                key="exhaust",
                symbol_type="generic",
                confidence=0.94,
                bbox=DetectionBBox(x=5, y=15, w=8, h=8),
                detector_type="template",
                match_metadata={},
            ),
        ],
        symbols=[symbol],
    )

    assert result.enriched_text == "[[symbol:exhaust]]: Gain\n[[symbol:exhaust]]: Draw"
    assert result.rendered_text == "{E}: Gain\n{E}: Draw"
