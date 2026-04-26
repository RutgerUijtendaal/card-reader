from __future__ import annotations

from typing import Any

from card_reader_core.models import Template, now_utc


def list_templates(_session: Any = None) -> list[Template]:
    return list(Template.objects.order_by("label"))


def get_template(_session: Any, entry_id: str) -> Template | None:
    return Template.objects.filter(id=entry_id).first()


def get_template_by_key(_session: Any, key: str) -> Template | None:
    return Template.objects.filter(key=key).first()


def template_key_exists(_session: Any, *, key: str, exclude_id: str | None = None) -> bool:
    query = Template.objects.filter(key=key)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    return query.exists()


def create_template(
    _session: Any,
    *,
    key: str,
    label: str,
    definition_json: str,
) -> Template:
    return Template.objects.create(key=key, label=label, definition_json=definition_json)


def update_template(
    _session: Any,
    *,
    entry_id: str,
    updates: dict[str, object],
) -> Template | None:
    row = get_template(None, entry_id)
    if row is None:
        return None
    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)
    row.updated_at = now_utc()
    row.save()
    return row


def delete_template(_session: Any, *, entry_id: str) -> bool:
    deleted, _ = Template.objects.filter(id=entry_id).delete()
    return deleted > 0
