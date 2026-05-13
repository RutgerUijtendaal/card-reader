from __future__ import annotations

from dataclasses import dataclass

from django.db import connection


@dataclass(frozen=True)
class SchemaCheckResult:
    missing_tables: list[str]
    missing_columns: dict[str, list[str]]

    @property
    def ok(self) -> bool:
        return not self.missing_tables and not self.missing_columns


EXPECTED_TABLE_COLUMNS = {
    "card": {"id", "key", "label", "latest_version_id", "created_at", "updated_at"},
    "import_job": {
        "id",
        "source_path",
        "template_id",
        "options_json",
        "status",
        "total_items",
        "processed_items",
        "created_at",
        "updated_at",
    },
    "import_job_item": {"id", "job_id", "source_file", "status", "error_message", "created_at", "updated_at"},
    "card_version": {
        "id",
        "card_id",
        "version_number",
        "template_id",
        "image_hash",
        "name",
        "type_line",
        "mana_cost",
        "mana_symbols_json",
        "attack",
        "health",
        "rules_text_raw",
        "rules_text_enriched",
        "rules_text",
        "confidence",
        "field_sources_json",
        "parsed_snapshot_json",
        "is_latest",
        "previous_version_id",
        "created_at",
        "updated_at",
    },
    "card_version_image": {
        "id",
        "card_version_id",
        "source_file",
        "stored_path",
        "width",
        "height",
        "checksum",
        "created_at",
        "updated_at",
    },
    "parse_result": {
        "id",
        "card_version_id",
        "raw_ocr_json",
        "normalized_fields_json",
        "confidence_json",
        "created_at",
        "updated_at",
    },
    "tag": {"id", "key", "label", "identifiers_json", "created_at", "updated_at"},
    "symbol": {
        "id",
        "key",
        "label",
        "symbol_type",
        "detector_type",
        "detection_config_json",
        "text_enrichment_json",
        "reference_assets_json",
        "text_token",
        "enabled",
        "created_at",
        "updated_at",
    },
    "keyword": {"id", "key", "label", "identifiers_json", "created_at", "updated_at"},
    "type": {"id", "key", "label", "identifiers_json", "created_at", "updated_at"},
    "card_version_tag": {"id", "card_version_id", "tag_id", "created_at", "updated_at"},
    "card_version_symbol": {"id", "card_version_id", "symbol_id", "created_at", "updated_at"},
    "card_version_keyword": {"id", "card_version_id", "keyword_id", "created_at", "updated_at"},
    "card_version_type": {"id", "card_version_id", "type_id", "created_at", "updated_at"},
    "template": {"id", "key", "label", "definition_json", "created_at", "updated_at"},
}


def check_existing_schema() -> SchemaCheckResult:
    existing_tables = set(connection.introspection.table_names())
    missing_tables = sorted(set(EXPECTED_TABLE_COLUMNS) - existing_tables)
    missing_columns: dict[str, list[str]] = {}

    for table, expected_columns in EXPECTED_TABLE_COLUMNS.items():
        if table in missing_tables:
            continue
        columns = {
            column.name
            for column in connection.introspection.get_table_description(connection.cursor(), table)
        }
        missing = sorted(expected_columns - columns)
        if missing:
            missing_columns[table] = missing

    return SchemaCheckResult(missing_tables=missing_tables, missing_columns=missing_columns)
