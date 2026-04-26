from __future__ import annotations

from card_reader_core.models import Template


def template_payload(row: Template) -> dict[str, object]:
    return {
        "id": row.id,
        "key": row.key,
        "label": row.label,
        "definition_json": row.definition_json,
    }
