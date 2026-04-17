from __future__ import annotations

from sqlalchemy import delete
from sqlmodel import Session, select

from models import (
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Keyword,
    Symbol,
    Tag,
    Type,
    now_utc,
)
from repositories.helpers import normalize_slug_key


def list_keywords(session: Session, *, keys: set[str] | None = None) -> list[Keyword]:
    if keys is not None and not keys:
        return []

    statement = select(Keyword).order_by(Keyword.label.asc())
    if keys is not None:
        statement = statement.where(Keyword.key.in_(keys))
    return list(session.exec(statement))


def list_tags(session: Session, *, keys: set[str] | None = None) -> list[Tag]:
    if keys is not None and not keys:
        return []

    statement = select(Tag).order_by(Tag.label.asc())
    if keys is not None:
        statement = statement.where(Tag.key.in_(keys))
    return list(session.exec(statement))


def list_symbols(session: Session, *, keys: set[str] | None = None) -> list[Symbol]:
    if keys is not None and not keys:
        return []

    statement = select(Symbol).order_by(Symbol.label.asc())
    if keys is not None:
        statement = statement.where(Symbol.key.in_(keys))
    return list(session.exec(statement))


def list_types(session: Session, *, keys: set[str] | None = None) -> list[Type]:
    if keys is not None and not keys:
        return []

    statement = select(Type).order_by(Type.label.asc())
    if keys is not None:
        statement = statement.where(Type.key.in_(keys))
    return list(session.exec(statement))


def replace_card_version_keywords(
    session: Session,
    *,
    card_version_id: str,
    keyword_ids: list[str],
) -> None:
    session.exec(
        delete(CardVersionKeyword).where(CardVersionKeyword.card_version_id == card_version_id)
    )

    seen: set[str] = set()
    for keyword_id in keyword_ids:
        if keyword_id in seen:
            continue
        seen.add(keyword_id)
        session.add(CardVersionKeyword(card_version_id=card_version_id, keyword_id=keyword_id))

    session.commit()


def replace_card_version_tags(
    session: Session,
    *,
    card_version_id: str,
    tag_ids: list[str],
) -> None:
    session.exec(delete(CardVersionTag).where(CardVersionTag.card_version_id == card_version_id))

    seen: set[str] = set()
    for tag_id in tag_ids:
        if tag_id in seen:
            continue
        seen.add(tag_id)
        session.add(CardVersionTag(card_version_id=card_version_id, tag_id=tag_id))

    session.commit()


def replace_card_version_types(
    session: Session,
    *,
    card_version_id: str,
    type_ids: list[str],
) -> None:
    session.exec(delete(CardVersionType).where(CardVersionType.card_version_id == card_version_id))

    seen: set[str] = set()
    for type_id in type_ids:
        if type_id in seen:
            continue
        seen.add(type_id)
        session.add(CardVersionType(card_version_id=card_version_id, type_id=type_id))

    session.commit()


def upsert_tags_by_labels(session: Session, labels: list[str]) -> list[Tag]:
    entries = _normalize_label_entries(labels)
    if not entries:
        return []

    keys = {key for key, _ in entries}
    existing_rows = session.exec(select(Tag).where(Tag.key.in_(keys)))
    existing_by_key = {row.key: row for row in existing_rows}

    out: list[Tag] = []
    for key, label in entries:
        existing = existing_by_key.get(key)
        if existing is None:
            created = Tag(key=key, label=label)
            session.add(created)
            session.flush()
            out.append(created)
            continue

        if existing.label != label:
            existing.label = label
            existing.updated_at = now_utc()
            session.add(existing)
        out.append(existing)

    session.commit()
    return out


def upsert_types_by_labels(session: Session, labels: list[str]) -> list[Type]:
    entries = _normalize_label_entries(labels)
    if not entries:
        return []

    keys = {key for key, _ in entries}
    existing_rows = session.exec(select(Type).where(Type.key.in_(keys)))
    existing_by_key = {row.key: row for row in existing_rows}

    out: list[Type] = []
    for key, label in entries:
        existing = existing_by_key.get(key)
        if existing is None:
            created = Type(key=key, label=label)
            session.add(created)
            session.flush()
            out.append(created)
            continue

        if existing.label != label:
            existing.label = label
            existing.updated_at = now_utc()
            session.add(existing)
        out.append(existing)

    session.commit()
    return out


def get_keywords_for_card_version(session: Session, card_version_id: str) -> list[Keyword]:
    statement = (
        select(Keyword)
        .join(CardVersionKeyword, CardVersionKeyword.keyword_id == Keyword.id)
        .where(CardVersionKeyword.card_version_id == card_version_id)
        .order_by(Keyword.label.asc())
    )
    return list(session.exec(statement))


def get_tags_for_card_version(session: Session, card_version_id: str) -> list[Tag]:
    statement = (
        select(Tag)
        .join(CardVersionTag, CardVersionTag.tag_id == Tag.id)
        .where(CardVersionTag.card_version_id == card_version_id)
        .order_by(Tag.label.asc())
    )
    return list(session.exec(statement))


def get_symbols_for_card_version(session: Session, card_version_id: str) -> list[Symbol]:
    statement = (
        select(Symbol)
        .join(CardVersionSymbol, CardVersionSymbol.symbol_id == Symbol.id)
        .where(CardVersionSymbol.card_version_id == card_version_id)
        .order_by(Symbol.label.asc())
    )
    return list(session.exec(statement))


def get_types_for_card_version(session: Session, card_version_id: str) -> list[Type]:
    statement = (
        select(Type)
        .join(CardVersionType, CardVersionType.type_id == Type.id)
        .where(CardVersionType.card_version_id == card_version_id)
        .order_by(Type.label.asc())
    )
    return list(session.exec(statement))


def _normalize_label_entries(labels: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in labels:
        label = " ".join(raw.split()).strip()
        if not label:
            continue
        key = normalize_slug_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((key, label))
    return out
