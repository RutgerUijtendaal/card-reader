from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from card_reader_core.models import CardVersion

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"
UNORDERED_LIST_PATH_SUFFIXES = {
    ".metadata.keywords",
    ".metadata.tags",
    ".metadata.symbols",
    ".metadata.types",
    ".snapshot.metadata.keywords",
    ".snapshot.metadata.tags",
    ".snapshot.metadata.symbols",
    ".snapshot.metadata.types",
    ".fields.mana_symbols",
}


def load_case_paths(cases_dir: Path) -> list[Path]:
    if not cases_dir.exists():
        return []
    return sorted(cases_dir.glob("*.json"))


def case_id(path: Path) -> str:
    return path.stem


def load_case(case_path: Path) -> dict[str, Any]:
    return json.loads(case_path.read_text(encoding="utf-8"))


def run_case(case_path: Path) -> dict[str, Any]:
    from card_reader_core.repositories.import_jobs_repository import create_import_job
    from card_reader_core.services.parser_jobs import ImportProcessorService
    from card_reader_parser.parsers.card_parser import CardParser

    case = load_case(case_path)
    image_path = (FIXTURES_ROOT / case["input"]["image"]).resolve()
    assert image_path.exists(), f"Fixture image does not exist: {image_path}"

    parser = CardParser()
    processor = ImportProcessorService(parser)
    job = create_import_job(
        source_path=image_path,
        template_id=str(case["input"]["template_key"]),
        options=_job_options(case),
    )
    processor.process_job(job.id)

    return load_db_state()


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
        if _is_unordered_list_path(path):
            assert sorted(actual) == sorted(expected), f"{path}: expected unordered values {sorted(expected)!r}, got {sorted(actual)!r}"
            return
        for index, expected_item in enumerate(expected):
            assert_recursive_exact(expected_item, actual[index], f"{path}[{index}]")
        return

    assert actual == expected, f"{path}: expected {expected!r}, got {actual!r}"


def load_db_state() -> dict[str, object]:
    from card_reader_core.models import Card, CardVersion, CardVersionMetadataSuggestion, ImportJob, ImportJobItem
    from card_reader_core.repositories.metadata_repository import (
        get_keywords_for_card_version,
        get_symbols_for_card_version,
        get_tags_for_card_version,
        get_types_for_card_version,
    )

    cards = list(Card.objects.order_by("-updated_at"))
    assert cards, "No card rows found after import processing"
    assert len(cards) == 1, f"Expected exactly one card row, found {len(cards)}"
    card = cards[0]

    latest_version = (
        CardVersion.objects.filter(card_id=card.id, is_latest=True)
        .select_related("template")
        .order_by("-version_number")
        .first()
    )
    assert latest_version is not None, "Latest card version not found"

    job = ImportJob.objects.order_by("-created_at").first()
    assert job is not None, "Expected import job row but none exists"
    item_rows: list[ImportJobItem] = list(ImportJobItem.objects.filter(job_id=job.id).order_by("created_at"))

    suggestion_rows = list(
        CardVersionMetadataSuggestion.objects.filter(card_version_id=latest_version.id)
        .select_related("suggestion")
        .order_by("suggestion__kind", "suggestion__normalized_value")
    )

    return {
        "card": {
            "key": card.key,
            "label": card.label,
        },
        "fields": {
            "template_key": latest_version.template.key,
            "name": latest_version.name,
            "type_line": latest_version.type_line,
            "mana_cost": latest_version.mana_cost,
            "mana_symbols": latest_version.mana_symbols_json,
            "attack": latest_version.attack,
            "health": latest_version.health,
            "rules_text_raw": latest_version.rules_text_raw,
            "rules_text_enriched": latest_version.rules_text_enriched,
            "rules_text": latest_version.rules_text,
            "version_number": latest_version.version_number,
        },
        "metadata": {
            "keywords": sorted(row.key for row in get_keywords_for_card_version(latest_version.id)),
            "tags": sorted(row.key for row in get_tags_for_card_version(latest_version.id)),
            "symbols": sorted(row.key for row in get_symbols_for_card_version(latest_version.id)),
            "types": sorted(row.key for row in get_types_for_card_version(latest_version.id)),
            "symbol_types": _load_symbol_types(latest_version.id),
        },
        "suggestions": {
            "tags": _normalize_suggestions(suggestion_rows, kind="tag"),
            "types": _normalize_suggestions(suggestion_rows, kind="type"),
        },
        "snapshot": _normalize_snapshot(latest_version),
        "field_sources": latest_version.field_sources_json,
        "job": {
            "status": str(job.status),
            "total_items": job.total_items,
            "processed_items": job.processed_items,
            "item_statuses": [str(row.status) for row in item_rows],
        },
    }


def _job_options(case: dict[str, Any]) -> dict[str, object]:
    options = case["input"].get("job_options", {})
    assert isinstance(options, dict), "case.input.job_options must be an object"
    return options


def _load_symbol_types(card_version_id: str) -> dict[str, str]:
    from card_reader_core.repositories.metadata_repository import get_symbols_for_card_version

    return {
        row.key: row.symbol_type
        for row in sorted(get_symbols_for_card_version(card_version_id), key=lambda row: row.key)
    }


def _normalize_suggestions(
    suggestion_rows: list[Any],
    *,
    kind: str,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for row in suggestion_rows:
        suggestion = row.suggestion
        if suggestion.kind != kind:
            continue
        normalized.append(
            {
                "normalized_value": suggestion.normalized_value,
                "display_value": suggestion.display_value,
                "source_text": row.source_text,
                "normalized_source_text": row.normalized_source_text,
                "status": suggestion.status,
            }
        )
    return normalized


def _normalize_snapshot(version: CardVersion) -> dict[str, object]:
    from card_reader_core.models import Keyword, Symbol, Tag, Type

    fields = version.parsed_snapshot_json.get("fields", {})
    metadata = version.parsed_snapshot_json.get("metadata", {})
    return {
        "fields": {
            "name": fields.get("name", ""),
            "type_line": fields.get("type_line", ""),
            "mana_cost": fields.get("mana_cost", ""),
            "attack": fields.get("attack"),
            "health": fields.get("health"),
            "rules_text": fields.get("rules_text", ""),
        },
        "metadata": {
            "keywords": sorted(_map_metadata_keys(metadata.get("keyword_ids"), Keyword)),
            "tags": sorted(_map_metadata_keys(metadata.get("tag_ids"), Tag)),
            "types": sorted(_map_metadata_keys(metadata.get("type_ids"), Type)),
            "symbols": sorted(_map_metadata_keys(metadata.get("symbol_ids"), Symbol)),
        },
    }


def _map_metadata_keys(raw_ids: object, model: type[Any]) -> list[str]:
    if not isinstance(raw_ids, list):
        return []
    keys_by_id = {str(row.id): row.key for row in model.objects.filter(id__in=[str(item) for item in raw_ids])}
    return [keys_by_id[str(item)] for item in raw_ids if str(item) in keys_by_id]


def _is_unordered_list_path(path: str) -> bool:
    return any(path.endswith(suffix) for suffix in UNORDERED_LIST_PATH_SUFFIXES)
