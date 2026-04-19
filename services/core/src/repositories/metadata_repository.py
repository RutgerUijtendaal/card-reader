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


def list_detectable_symbols(session: Session) -> list[Symbol]:
    statement = (
        select(Symbol)
        .where(Symbol.enabled.is_(True), Symbol.detector_type == "template")
        .order_by(Symbol.label.asc())
    )
    return list(session.exec(statement))


def list_types(session: Session, *, keys: set[str] | None = None) -> list[Type]:
    if keys is not None and not keys:
        return []

    statement = select(Type).order_by(Type.label.asc())
    if keys is not None:
        statement = statement.where(Type.key.in_(keys))
    return list(session.exec(statement))


def get_keyword(session: Session, entry_id: str) -> Keyword | None:
    return session.get(Keyword, entry_id)


def get_tag(session: Session, entry_id: str) -> Tag | None:
    return session.get(Tag, entry_id)


def get_symbol(session: Session, entry_id: str) -> Symbol | None:
    return session.get(Symbol, entry_id)


def get_type(session: Session, entry_id: str) -> Type | None:
    return session.get(Type, entry_id)


def keyword_key_exists(session: Session, *, key: str, exclude_id: str | None = None) -> bool:
    existing = session.exec(select(Keyword).where(Keyword.key == key)).first()
    if existing is None:
        return False
    if exclude_id is not None and existing.id == exclude_id:
        return False
    return True


def tag_key_exists(session: Session, *, key: str, exclude_id: str | None = None) -> bool:
    existing = session.exec(select(Tag).where(Tag.key == key)).first()
    if existing is None:
        return False
    if exclude_id is not None and existing.id == exclude_id:
        return False
    return True


def symbol_key_exists(session: Session, *, key: str, exclude_id: str | None = None) -> bool:
    existing = session.exec(select(Symbol).where(Symbol.key == key)).first()
    if existing is None:
        return False
    if exclude_id is not None and existing.id == exclude_id:
        return False
    return True


def type_key_exists(session: Session, *, key: str, exclude_id: str | None = None) -> bool:
    existing = session.exec(select(Type).where(Type.key == key)).first()
    if existing is None:
        return False
    if exclude_id is not None and existing.id == exclude_id:
        return False
    return True


def create_keyword(session: Session, *, key: str, label: str) -> Keyword:
    row = Keyword(key=key, label=label)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_tag(session: Session, *, key: str, label: str) -> Tag:
    row = Tag(key=key, label=label)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_type(session: Session, *, key: str, label: str) -> Type:
    row = Type(key=key, label=label)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_symbol(
    session: Session,
    *,
    key: str,
    label: str,
    symbol_type: str,
    detector_type: str,
    detection_config_json: str,
    reference_assets_json: str,
    text_token: str,
    enabled: bool,
) -> Symbol:
    row = Symbol(
        key=key,
        label=label,
        symbol_type=symbol_type,
        detector_type=detector_type,
        detection_config_json=detection_config_json,
        reference_assets_json=reference_assets_json,
        text_token=text_token,
        enabled=enabled,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_keyword(
    session: Session,
    *,
    entry_id: str,
    updates: dict[str, object],
) -> Keyword | None:
    row = get_keyword(session, entry_id)
    if row is None:
        return None

    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)

    row.updated_at = now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_tag(
    session: Session,
    *,
    entry_id: str,
    updates: dict[str, object],
) -> Tag | None:
    row = get_tag(session, entry_id)
    if row is None:
        return None

    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)

    row.updated_at = now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_type(
    session: Session,
    *,
    entry_id: str,
    updates: dict[str, object],
) -> Type | None:
    row = get_type(session, entry_id)
    if row is None:
        return None

    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)

    row.updated_at = now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_symbol(
    session: Session,
    *,
    entry_id: str,
    updates: dict[str, object],
) -> Symbol | None:
    row = get_symbol(session, entry_id)
    if row is None:
        return None

    for field_name, field_value in updates.items():
        setattr(row, field_name, field_value)

    row.updated_at = now_utc()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_keyword(session: Session, *, entry_id: str) -> bool:
    row = get_keyword(session, entry_id)
    if row is None:
        return False
    session.exec(delete(CardVersionKeyword).where(CardVersionKeyword.keyword_id == entry_id))
    session.delete(row)
    session.commit()
    return True


def delete_tag(session: Session, *, entry_id: str) -> bool:
    row = get_tag(session, entry_id)
    if row is None:
        return False
    session.exec(delete(CardVersionTag).where(CardVersionTag.tag_id == entry_id))
    session.delete(row)
    session.commit()
    return True


def delete_type(session: Session, *, entry_id: str) -> bool:
    row = get_type(session, entry_id)
    if row is None:
        return False
    session.exec(delete(CardVersionType).where(CardVersionType.type_id == entry_id))
    session.delete(row)
    session.commit()
    return True


def delete_symbol(session: Session, *, entry_id: str) -> bool:
    row = get_symbol(session, entry_id)
    if row is None:
        return False
    session.exec(delete(CardVersionSymbol).where(CardVersionSymbol.symbol_id == entry_id))
    session.delete(row)
    session.commit()
    return True


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


def replace_card_version_symbols(
    session: Session,
    *,
    card_version_id: str,
    symbol_ids: list[str],
) -> None:
    session.exec(delete(CardVersionSymbol).where(CardVersionSymbol.card_version_id == card_version_id))

    seen: set[str] = set()
    for symbol_id in symbol_ids:
        if symbol_id in seen:
            continue
        seen.add(symbol_id)
        session.add(CardVersionSymbol(card_version_id=card_version_id, symbol_id=symbol_id))

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
