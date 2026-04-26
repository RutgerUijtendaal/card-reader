from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from card_reader_core.database.connection import get_session
from card_reader_core.models import Card, CardVersion, ImportJob, ImportJobItem, Symbol
from card_reader_parser.parsers.card_parser import CardParser
from card_reader_core.repositories import (
    create_import_job,
    get_keywords_for_card_version,
    get_symbols_for_card_version,
    get_tags_for_card_version,
    get_types_for_card_version,
)
from card_reader_core.services import ImportProcessorService
from card_reader_parser.template_store import DatabaseTemplateStore

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"


def load_case_paths(cases_dir: Path) -> list[Path]:
    if not cases_dir.exists():
        return []
    return sorted(cases_dir.glob("*.json"))


def case_id(path: Path) -> str:
    return path.stem


def run_case(case_path: Path) -> dict[str, Any]:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    image_path = (FIXTURES_ROOT / case["image"]).resolve()
    assert image_path.exists(), f"Fixture image does not exist: {image_path}"

    parser = CardParser(DatabaseTemplateStore())

    processor = ImportProcessorService(parser)
    with get_session() as session:
        job = create_import_job(
            session,
            source_path=image_path,
            template_id=str(case["template_id"]),
            options=case.get("job_options", {}),
        )
        processor.process_job(session, job.id)

    with get_session() as session:
        return _load_db_state(session=session)


def assert_recursive_exact(expected: Any, actual: Any, path: str = "root") -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected dict, got {type(actual).__name__}"
        assert set(actual.keys()) == set(expected.keys()), (
            f"{path}: expected keys {sorted(expected.keys())}, got {sorted(actual.keys())}"
        )
        for key, expected_value in expected.items():
            assert_recursive_exact(expected_value, actual[key], f"{path}.{key}")
        return

    if isinstance(expected, list):
        assert isinstance(actual, list), f"{path}: expected list, got {type(actual).__name__}"
        assert len(actual) == len(expected), f"{path}: expected list length {len(expected)}, got {len(actual)}"
        for index, expected_item in enumerate(expected):
            assert_recursive_exact(expected_item, actual[index], f"{path}[{index}]")
        return

    assert actual == expected, f"{path}: expected {expected!r}, got {actual!r}"


def _load_db_state(*, session: Any) -> dict[str, Any]:
    cards = list(Card.objects.order_by("-updated_at"))
    assert cards, "No card rows found after import processing"
    assert len(cards) == 1, f"Expected exactly one card row, found {len(cards)}"
    card = cards[0]

    latest_version = (
        CardVersion.objects.filter(card_id=card.id, is_latest=True)
        .order_by("-version_number")
        .first()
    )
    assert latest_version is not None, "Latest card version not found"

    job = ImportJob.objects.order_by("-created_at").first()
    assert job is not None, "Expected import job row but none exists"
    item_rows: list[ImportJobItem] = list(ImportJobItem.objects.filter(job_id=job.id))

    keywords = sorted(row.label for row in get_keywords_for_card_version(session, latest_version.id))
    tags = sorted(row.label for row in get_tags_for_card_version(session, latest_version.id))
    symbols = sorted(row.key for row in get_symbols_for_card_version(session, latest_version.id))
    types = sorted(row.label for row in get_types_for_card_version(session, latest_version.id))

    all_symbol_types = {row.key: row.symbol_type for row in Symbol.objects.all()}

    return {
        "card": {
            "key": card.key,
            "label": card.label,
        },
        "latest_version": {
            "template_id": latest_version.template_id,
            "name": latest_version.name,
            "type_line": latest_version.type_line,
            "mana_cost": latest_version.mana_cost,
            "mana_symbols": json.loads(latest_version.mana_symbols_json or "[]"),
            "attack": latest_version.attack,
            "health": latest_version.health,
            "rules_text": latest_version.rules_text,
            "version_number": latest_version.version_number,
        },
        "metadata": {
            "keywords": keywords,
            "tags": tags,
            "symbols": symbols,
            "types": types,
            "symbol_types": {key: all_symbol_types.get(key, "") for key in symbols},
        },
        "job": {
            "status": str(job.status),
            "total_items": job.total_items,
            "processed_items": job.processed_items,
            "item_statuses": [str(row.status) for row in item_rows],
        },
    }
