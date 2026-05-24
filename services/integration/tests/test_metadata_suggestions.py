from __future__ import annotations

from pathlib import Path

from catalog_seed import seed_integration_catalog
from helpers import load_case, run_case

CASE_PATH = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases" / "silver_stake_full_flow_case.json"


def test_unknown_catalog_entries_persist_metadata_suggestions() -> None:
    from card_reader_core.models import CardVersionMetadataSuggestion

    seed_integration_catalog(omit_tag_keys={"silver"})

    case = load_case(CASE_PATH)
    state = run_case(CASE_PATH)

    assert state["metadata"]["tags"] == ["weapon"]
    assert state["suggestions"]["tags"] == [
        {
            "normalized_value": "silver",
            "display_value": "silver",
            "source_text": case["expected"]["fields"]["type_line"],
            "normalized_source_text": "equipment silver weapon",
            "status": "pending",
        }
    ]
    assert CardVersionMetadataSuggestion.objects.count() == 1
