from __future__ import annotations

from typing import Any, TypedDict

from card_reader_core.models import ImportJobItem

MATCHED_DEPRECATED_CARD_WARNING = "matched_deprecated_card"
CARD_CLASSIFICATION_MISMATCH_WARNING = "card_classification_mismatch"
CARD_CLASSIFICATION_CHANGED_WHILE_QUEUED_WARNING = "card_classification_changed_while_queued"
_WARNING_ORDER = (
    MATCHED_DEPRECATED_CARD_WARNING,
    CARD_CLASSIFICATION_MISMATCH_WARNING,
    CARD_CLASSIFICATION_CHANGED_WHILE_QUEUED_WARNING,
)


class ImportWarning(TypedDict, total=False):
    code: str
    message: str
    details: dict[str, Any]


def normalized_import_warnings(value: object) -> list[ImportWarning]:
    if not isinstance(value, list):
        return []
    normalized: dict[str, ImportWarning] = {}
    for row in value:
        if not isinstance(row, dict):
            continue
        code = row.get("code")
        message = row.get("message")
        if not isinstance(code, str) or not code.strip() or not isinstance(message, str):
            continue
        warning: ImportWarning = {"code": code.strip(), "message": message.strip()}
        details = row.get("details")
        if isinstance(details, dict):
            warning["details"] = details
        normalized[warning["code"]] = warning
    order = {code: index for index, code in enumerate(_WARNING_ORDER)}
    return sorted(normalized.values(), key=lambda warning: (order.get(warning["code"], 100), warning["code"]))


def upsert_import_warning(item: ImportJobItem, warning: ImportWarning) -> None:
    warnings = {
        row["code"]: row
        for row in normalized_import_warnings(item.warnings_json)
    }
    warnings[warning["code"]] = warning
    item.warnings_json = normalized_import_warnings(list(warnings.values()))
    _sync_legacy_warning_fields(item)


def remove_import_warning(item: ImportJobItem, code: str) -> None:
    item.warnings_json = [
        warning for warning in normalized_import_warnings(item.warnings_json) if warning["code"] != code
    ]
    _sync_legacy_warning_fields(item)


def _sync_legacy_warning_fields(item: ImportJobItem) -> None:
    warnings = normalized_import_warnings(item.warnings_json)
    first = warnings[0] if warnings else None
    item.warning_code = first["code"] if first else None
    item.warning_message = first["message"] if first else None
