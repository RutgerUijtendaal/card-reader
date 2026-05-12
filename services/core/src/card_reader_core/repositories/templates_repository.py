from __future__ import annotations

from card_reader_core.models import Template, now_utc


def list_templates() -> list[Template]:
    return list(Template.objects.order_by("label"))


def get_template(entry_id: str) -> Template | None:
    return Template.objects.filter(id=entry_id).first()


def get_template_by_key(*, key: str) -> Template | None:
    return Template.objects.filter(key=key).first()


def template_key_exists(*, key: str, exclude_id: str | None = None) -> bool:
    query = Template.objects.filter(key=key)
    if exclude_id is not None:
        query = query.exclude(id=exclude_id)
    return query.exists()


def create_template(
    *,
    key: str,
    label: str,
    definition_json: dict[str, object],
) -> Template:
    return Template.objects.create(key=key, label=label, definition_json=definition_json)


def update_template(
    *,
    entry_id: str,
    updates: dict[str, object],
) -> Template | None:
    row = get_template(entry_id)
    if row is None:
        return None
    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)
    row.updated_at = now_utc()
    row.save()
    return row


def delete_template(*, entry_id: str) -> bool:
    deleted, _ = Template.objects.filter(id=entry_id).delete()
    return deleted > 0
