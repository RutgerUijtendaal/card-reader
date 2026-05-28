from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from helpers import FIXTURES_ROOT, load_case, load_db_state

CASE_PATH = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases" / "silver_stake_full_flow_case.json"


def test_reparse_preserves_manual_fields_and_metadata_groups() -> None:
    from card_reader_core.repositories.cards import get_latest_card_version, update_latest_card_version
    from card_reader_core.repositories.import_jobs import create_import_job
    from card_reader_core.repositories.metadata import get_tags_for_card_version
    from card_reader_core.services.parser_jobs import ImportProcessorService
    from card_reader_parser.parsers.card_parser import CardParser

    case = load_case(CASE_PATH)
    image_path = (FIXTURES_ROOT / case["input"]["image"]).resolve()

    parser = CardParser()
    processor = ImportProcessorService(parser)

    first_job = create_import_job(
        source_path=image_path,
        template_id=str(case["input"]["template_key"]),
        options=case["input"]["job_options"],
    )
    processor.process_job(first_job.id)

    latest = get_latest_card_version(_latest_card_id())
    assert latest is not None
    original_snapshot = cast(dict[str, Any], latest.parsed_snapshot_json)
    original_tag_keys = _snapshot_metadata_tags(load_db_state())
    assert original_tag_keys

    first_tag = get_tags_for_card_version(latest.id)[0]
    update_latest_card_version(
        card_id=latest.card.id,
        updates={
            "rules_text": "Manual lock text",
            "tag_ids": [first_tag.id],
        },
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
    )

    second_job = create_import_job(
        source_path=image_path,
        template_id=str(case["input"]["template_key"]),
        options=case["input"]["job_options"],
    )
    processor.process_job(second_job.id)

    reparsed = get_latest_card_version(latest.card.id)
    assert reparsed is not None
    reparsed_state = load_db_state()

    assert reparsed.rules_text == "Manual lock text"
    assert _state_metadata_tags(reparsed_state) == ["silver"]
    assert reparsed.field_sources_json["fields"]["rules_text"] == "manual"
    assert reparsed.field_sources_json["metadata"]["tags"] == "manual"
    assert cast(dict[str, Any], original_snapshot["metadata"])["tag_ids"]
    assert _snapshot_rules_text(reparsed_state) != reparsed.rules_text
    assert _snapshot_metadata_tags(reparsed_state) == original_tag_keys


def test_targeted_reparse_can_switch_template_without_creating_new_version() -> None:
    from card_reader_core.models import Template
    from card_reader_core.repositories.cards import get_latest_card_version, update_latest_card_version
    from card_reader_core.repositories.import_jobs import (
        ImportJobItemTarget,
        create_import_job,
        create_import_job_with_files,
    )
    from card_reader_core.services.parser_jobs import ImportProcessorService
    from card_reader_parser.parsers.card_parser import CardParser

    case = load_case(CASE_PATH)
    image_path = (FIXTURES_ROOT / case["input"]["image"]).resolve()

    parser = CardParser()
    processor = ImportProcessorService(parser)

    first_job = create_import_job(
        source_path=image_path,
        template_id=str(case["input"]["template_key"]),
        options=case["input"]["job_options"],
    )
    processor.process_job(first_job.id)

    latest = get_latest_card_version(_latest_card_id())
    assert latest is not None
    original_version_id = latest.id
    original_version_number = latest.version_number

    update_latest_card_version(
        card_id=latest.card.id,
        updates={"rules_text": "Manual template switch text"},
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
    )

    alt_template = Template.objects.create(
        key="silver-stake-alt-template",
        label="Silver Stake Alt Template",
        definition_json={
            "id": "silver-stake-alt-template",
            "version": 7,
            "regions": [
                {
                    "region_id": "top_bar",
                    "parser_type": "name_mana_cost",
                    "cut_region": {"unit": "relative", "x": 0.04, "y": 0.02, "w": 0.92, "h": 0.07},
                    "ocr_config": {},
                },
                {
                    "region_id": "type_bar",
                    "parser_type": "type_tag",
                    "cut_region": {"unit": "relative", "x": 0.04, "y": 0.54, "w": 0.92, "h": 0.05},
                    "ocr_config": {},
                },
                {
                    "region_id": "rules_text",
                    "parser_type": "rules_text",
                    "cut_region": {"unit": "relative", "x": 0.07, "y": 0.60, "w": 0.86, "h": 0.32},
                    "ocr_config": {},
                },
            ],
        },
    )

    second_job = create_import_job_with_files(
        source_path=image_path.parent / "targeted-reparse",
        template_id=alt_template.key,
        options={"reparse_existing": True},
        files=[image_path],
        item_targets=[ImportJobItemTarget(card_id=latest.card.id, card_version_id=latest.id)],
    )
    processor.process_job(second_job.id)

    reparsed = get_latest_card_version(latest.card.id)
    assert reparsed is not None
    reparsed_state = load_db_state()

    assert reparsed.id == original_version_id
    assert reparsed.version_number == original_version_number
    assert reparsed.template.key == alt_template.key
    assert reparsed.rules_text != "Manual template switch text"
    assert reparsed.field_sources_json["fields"]["rules_text"] == "auto"
    assert _field_source_rules_text(reparsed_state) == "auto"
    assert _snapshot_rules_text(reparsed_state) == reparsed.rules_text_enriched


def _latest_card_id() -> str:
    from card_reader_core.models import Card

    card = Card.objects.order_by("-updated_at").first()
    assert card is not None
    return card.id


def _snapshot_metadata_tags(state: dict[str, object]) -> list[str]:
    snapshot = cast(dict[str, object], state["snapshot"])
    metadata = cast(dict[str, object], snapshot["metadata"])
    return cast(list[str], metadata["tags"])


def _snapshot_rules_text(state: dict[str, object]) -> str:
    snapshot = cast(dict[str, object], state["snapshot"])
    fields = cast(dict[str, object], snapshot["fields"])
    return cast(str, fields["rules_text"])


def _state_metadata_tags(state: dict[str, object]) -> list[str]:
    metadata = cast(dict[str, object], state["metadata"])
    return cast(list[str], metadata["tags"])


def _field_source_rules_text(state: dict[str, object]) -> str:
    field_sources = cast(dict[str, object], state["field_sources"])
    fields = cast(dict[str, object], field_sources["fields"])
    return cast(str, fields["rules_text"])
