from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, select

from models import Template, now_utc
from repositories import normalize_slug_key
from seeds.shared import resolve_seed_file

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES_FILE = resolve_seed_file("templates.json")


@dataclass(slots=True)
class TemplateSeedEntry:
    key: str
    label: str
    definition_json: str


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
        if not label:
            continue

        raw_key = str(item.get("key", "")).strip() or label
        key = normalize_slug_key(raw_key)
        if not key or key in seen_keys:
            continue

        definition = item.get("definition")
        if not isinstance(definition, dict):
            continue

        out.append(
            TemplateSeedEntry(
                key=key,
                label=label,
                definition_json=json.dumps(definition),
            )
        )
        seen_keys.add(key)

    return out


def seed_templates(session: Session) -> tuple[int, int]:
    entries = read_template_entries()
    if not entries:
        return 0, 0

    created = 0
    updated = 0
    keys = {entry.key for entry in entries}
    existing_rows = session.exec(select(Template).where(Template.key.in_(keys)))
    existing_by_key = {row.key: row for row in existing_rows}

    for entry in entries:
        existing = existing_by_key.get(entry.key)
        if existing is None:
            session.add(
                Template(
                    key=entry.key,
                    label=entry.label,
                    definition_json=entry.definition_json,
                )
            )
            created += 1
            continue

        changed = False
        changed |= _set_if_diff(existing, "label", entry.label)
        changed |= _set_if_diff(existing, "definition_json", entry.definition_json)
        if changed:
            existing.updated_at = now_utc()
            session.add(existing)
            updated += 1

    session.commit()
    return created, updated


def template_table_has_rows(session: Session) -> bool:
    return session.exec(select(Template.id).limit(1)).first() is not None


def _set_if_diff(instance: Template, field_name: str, value: object) -> bool:
    if getattr(instance, field_name) == value:
        return False
    setattr(instance, field_name, value)
    return True
