from __future__ import annotations

from pathlib import Path

from helpers import load_case, run_case

CASE_PATH = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases" / "silver_stake_full_flow_case.json"


def test_unknown_catalog_entries_persist_metadata_suggestions() -> None:
    from card_reader_core.models import CardVersionMetadataSuggestion, Tag

    Tag.objects.filter(key="silver").delete()

    case = load_case(CASE_PATH)
    state = run_case(CASE_PATH)

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
