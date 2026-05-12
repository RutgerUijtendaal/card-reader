from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from card_reader_core.models import Template, now_utc
from card_reader_core.repositories.helpers import normalize_slug_key
from .shared import resolve_seed_file

logger = logging.getLogger(__name__)
DEFAULT_TEMPLATES_FILE = resolve_seed_file("seed-templates.json")


@dataclass(slots=True)
class TemplateSeedEntry:
    key: str
    label: str
    definition_json: dict[str, object]


def read_template_entries(seed_file: Path = DEFAULT_TEMPLATES_FILE) -> list[TemplateSeedEntry]:
    if not seed_file.exists():
        logger.warning("Template seed file not found; skipping. file=%s", seed_file)
        return []
    try:
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.exception("Invalid template seed json. file=%s", seed_file)
        return []
    if not isinstance(payload, list):
        logger.warning("Template seed json must be an array. file=%s", seed_file)
        return []

    out: list[TemplateSeedEntry] = []
    seen_keys: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        key = normalize_slug_key(str(item.get("key", "")).strip() or label)
        definition = item.get("definition")
        if not label or not key or key in seen_keys or not isinstance(definition, dict):
            continue
        out.append(TemplateSeedEntry(key=key, label=label, definition_json=definition))
        seen_keys.add(key)
    return out


def seed_templates() -> tuple[int, int]:
    entries = read_template_entries()
    if not entries:
        return 0, 0
    existing_by_key = {row.key: row for row in Template.objects.filter(key__in=[entry.key for entry in entries])}
    created = 0
    updated = 0
    for entry in entries:
        existing = existing_by_key.get(entry.key)
        if existing is None:
            Template.objects.create(
                key=entry.key,
                label=entry.label,
                definition_json=entry.definition_json,
            )
            created += 1
            continue
        changed = False
        changed |= _set_if_diff(existing, "label", entry.label)
        changed |= _set_if_diff(existing, "definition_json", entry.definition_json)
        if changed:
            existing.updated_at = now_utc()
            existing.save()
            updated += 1
    return created, updated


def template_table_has_rows() -> bool:
    return Template.objects.exists()


def _set_if_diff(instance: Template, field_name: str, value: object) -> bool:
    if getattr(instance, field_name) == value:
        return False
    setattr(instance, field_name, value)
    return True
