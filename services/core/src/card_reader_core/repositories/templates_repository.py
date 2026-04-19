from __future__ import annotations

from sqlalchemy import asc
from sqlmodel import Session, col, select

from ..models import Template, now_utc


def list_templates(session: Session) -> list[Template]:
    statement = select(Template).order_by(asc(col(Template.label)))
    return list(session.exec(statement))


def get_template(session: Session, entry_id: str) -> Template | None:
    return session.get(Template, entry_id)


def get_template_by_key(session: Session, key: str) -> Template | None:
    statement = select(Template).where(col(Template.key) == key)
    return session.exec(statement).first()


def template_key_exists(session: Session, *, key: str, exclude_id: str | None = None) -> bool:
    existing = get_template_by_key(session, key)
    if existing is None:
        return False
    if exclude_id is not None and existing.id == exclude_id:
        return False
    return True


def create_template(
    session: Session,
    *,
    key: str,
    label: str,
    definition_json: str,
) -> Template:
    row = Template(key=key, label=label, definition_json=definition_json)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_template(
    session: Session,
    *,
    entry_id: str,
    updates: dict[str, object],
) -> Template | None:
    row = get_template(session, entry_id)
    if row is None:
        return None

    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)

    row.updated_at = now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_template(session: Session, *, entry_id: str) -> bool:
    row = get_template(session, entry_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True
