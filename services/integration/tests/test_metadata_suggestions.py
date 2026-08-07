from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from helpers import run_case

if TYPE_CHECKING:
    from card_reader_parser.parsers.card_parser import CardParser

CASE_PATH = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases" / "silver_stake_full_flow_case.json"


def test_unknown_catalog_entries_persist_metadata_suggestions(
    integration_card_parser: CardParser,
) -> None:
    from card_reader_core.models import CardVersionMetadataSuggestion, Tag

    Tag.objects.filter(key="silver").delete()

    state = run_case(CASE_PATH, integration_card_parser)

    assert state["metadata"]["tags"] == ["weapon"]
    assert state["suggestions"]["tags"] == [
        {
            "normalized_value": "silver",
            "display_value": "Silver",
            "source_text": "Silver Weapon",
            "normalized_source_text": "Silver Weapon",
            "status": "pending",
        }
    ]
    assert CardVersionMetadataSuggestion.objects.count() == 1
