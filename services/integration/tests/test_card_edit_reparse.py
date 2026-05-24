from __future__ import annotations

import json
from pathlib import Path

from card_reader_core.models import Template
from card_reader_core.repositories.cards_repository import get_latest_card_version, update_latest_card_version
from card_reader_core.repositories.import_jobs_repository import ImportJobItemTarget, create_import_job, create_import_job_with_files
from card_reader_core.repositories.metadata_repository import get_tags_for_card_version
from card_reader_core.services.parser_jobs import ImportProcessorService
from card_reader_parser.parsers.card_parser import CardParser

from helpers import FIXTURES_ROOT


def test_reparse_preserves_manual_fields_and_metadata_groups() -> None:
    case_path = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases" / "silver_stake_full_flow_case.json"
    case = json.loads(case_path.read_text(encoding="utf-8"))
    image_path = (FIXTURES_ROOT / case["image"]).resolve()

    parser = CardParser()
    processor = ImportProcessorService(parser)

    first_job = create_import_job(
        source_path=image_path,
        template_id=str(case["template_id"]),
        options=case.get("job_options", {}),
    )
    processor.process_job(first_job.id)

    latest = get_latest_card_version(_latest_card_id())
    assert latest is not None
    original_snapshot = latest.parsed_snapshot_json
    original_tag_ids = original_snapshot["metadata"]["tag_ids"]
    assert original_tag_ids

    update_latest_card_version(
        card_id=latest.card_id,
        updates={
            "rules_text": "Manual lock text",
            "tag_ids": [original_tag_ids[0]],
        },
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
    )

    second_job = create_import_job(
        source_path=image_path,
        template_id=str(case["template_id"]),
        options=case.get("job_options", {}),
    )
    processor.process_job(second_job.id)

    reparsed = get_latest_card_version(latest.card_id)
    assert reparsed is not None
    reparsed_snapshot = reparsed.parsed_snapshot_json

    assert reparsed.rules_text == "Manual lock text"
    assert [row.id for row in get_tags_for_card_version(reparsed.id)] == [original_tag_ids[0]]
    assert reparsed.field_sources_json
    assert reparsed_snapshot["fields"]["rules_text"] != reparsed.rules_text
    assert reparsed_snapshot["metadata"]["tag_ids"] == original_tag_ids


def test_targeted_reparse_can_switch_template_without_creating_new_version() -> None:
    case_path = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases" / "silver_stake_full_flow_case.json"
    case = json.loads(case_path.read_text(encoding="utf-8"))
    image_path = (FIXTURES_ROOT / case["image"]).resolve()

    parser = CardParser()
    processor = ImportProcessorService(parser)

    first_job = create_import_job(
        source_path=image_path,
        template_id=str(case["template_id"]),
        options=case.get("job_options", {}),
    )
    processor.process_job(first_job.id)

    latest = get_latest_card_version(_latest_card_id())
    assert latest is not None
    original_version_id = latest.id
    original_version_number = latest.version_number

    update_latest_card_version(
        card_id=latest.card_id,
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
            "regions": case["template_definition"]["regions"] if "template_definition" in case else [
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
                    "cut_region": {"unit": "relative", "x": 0.07, "y": 0.6, "w": 0.86, "h": 0.32},
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
        item_targets=[ImportJobItemTarget(card_id=latest.card_id, card_version_id=latest.id)],
    )
    processor.process_job(second_job.id)

    reparsed = get_latest_card_version(latest.card_id)
    assert reparsed is not None
    assert reparsed.id == original_version_id
    assert reparsed.version_number == original_version_number
    assert reparsed.template.key == alt_template.key
    assert reparsed.rules_text != "Manual template switch text"
    assert reparsed.field_sources_json["fields"]["rules_text"] == "auto"


def _latest_card_id() -> str:
    from card_reader_core.models import Card

    card = Card.objects.order_by("-updated_at").first()
    assert card is not None
    return card.id
