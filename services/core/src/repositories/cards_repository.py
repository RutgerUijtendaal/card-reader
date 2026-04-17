from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, select

from models import (
    Card,
    CardVersion,
    CardVersionImage,
    ImportJobItem,
    ImportJobStatus,
    ParseResult,
    now_utc,
)
from repositories.helpers import (
    extract_mana_symbols,
    normalize_slug_key,
    to_int_or_none,
)
from storage import store_image


def save_parsed_card(
    session: Session,
    *,
    item: ImportJobItem,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    reparse_existing: bool = True,
) -> CardVersion:
    parsed_name = normalized_fields.get("name", "").strip() or Path(item.source_file).stem
    card_key = normalize_slug_key(parsed_name)
    card = session.exec(select(Card).where(Card.key == card_key)).first()
    if card is None:
        card = Card(key=card_key, label=parsed_name)
        session.add(card)
        session.flush()

    latest_version = get_latest_card_version(session, card.id)

    if latest_version and latest_version.image_hash == checksum and reparse_existing:
        apply_parsed_fields_to_version(latest_version, normalized_fields=normalized_fields, confidence=confidence)
        parse_result = ParseResult(
            card_version_id=latest_version.id,
            raw_ocr_json=json.dumps(raw_ocr),
            normalized_fields_json=json.dumps(normalized_fields),
            confidence_json=json.dumps(confidence),
        )
        session.add(parse_result)
        session.flush()
        latest_version.parse_result_id = parse_result.id
        latest_version.updated_at = now_utc()
        session.add(latest_version)
        upsert_card_search(session, card_id=card.id, version=latest_version)

        item.status = ImportJobStatus.completed
        item.error_message = None
        item.updated_at = now_utc()
        session.add(item)
        session.commit()
        session.refresh(latest_version)
        return latest_version

    source_file_path = Path(item.source_file)
    stored_path = store_image(source_file_path, checksum)

    if latest_version is not None:
        latest_version.is_latest = False
        latest_version.updated_at = now_utc()
        session.add(latest_version)
        version_number = latest_version.version_number + 1
        previous_version_id = latest_version.id
    else:
        version_number = 1
        previous_version_id = None

    version = CardVersion(
        card_id=card.id,
        version_number=version_number,
        template_id=template_id,
        image_hash=checksum,
        name=parsed_name,
        type_line=normalized_fields.get("type_line", ""),
        mana_cost=normalized_fields.get("mana_cost", ""),
        mana_symbols_json=json.dumps(extract_mana_symbols(normalized_fields)),
        attack=to_int_or_none(normalized_fields.get("attack")),
        health=to_int_or_none(normalized_fields.get("health")),
        rules_text=normalized_fields.get("rules_text", ""),
        confidence=float(confidence.get("overall", 0.0)),
        is_latest=True,
        previous_version_id=previous_version_id,
    )
    session.add(version)
    session.flush()

    parse_result = ParseResult(
        card_version_id=version.id,
        raw_ocr_json=json.dumps(raw_ocr),
        normalized_fields_json=json.dumps(normalized_fields),
        confidence_json=json.dumps(confidence),
    )
    session.add(parse_result)
    session.flush()

    version.parse_result_id = parse_result.id
    session.add(version)

    image_record = CardVersionImage(
        card_version_id=version.id,
        source_file=item.source_file,
        stored_path=str(stored_path),
        checksum=checksum,
        updated_at=now_utc(),
    )
    session.add(image_record)

    card.label = parsed_name
    card.latest_version_id = version.id
    card.updated_at = now_utc()
    session.add(card)

    item.status = ImportJobStatus.completed
    item.error_message = None
    item.updated_at = now_utc()
    session.add(item)

    upsert_card_search(session, card_id=card.id, version=version)

    session.commit()
    session.refresh(version)
    return version


def list_cards(
    session: Session,
    *,
    query: str | None,
    max_confidence: float | None,
) -> list[tuple[Card, CardVersion]]:
    if query:
        rows = session.exec(
            text("SELECT card_id FROM card_version_search WHERE card_version_search MATCH :query"),
            params={"query": query},
        )
        card_ids = [row[0] for row in rows]
        if not card_ids:
            return []
        cards = list(session.exec(select(Card).where(Card.id.in_(card_ids))))
    else:
        cards = list(session.exec(select(Card).order_by(Card.updated_at.desc())))

    out: list[tuple[Card, CardVersion]] = []
    for card in cards:
        version = get_latest_card_version(session, card.id)
        if version is None:
            continue
        if max_confidence is not None and version.confidence > max_confidence:
            continue
        out.append((card, version))
    return out


def get_card(session: Session, card_id: str) -> Card | None:
    return session.get(Card, card_id)


def get_latest_card_version(session: Session, card_id: str) -> CardVersion | None:
    statement = (
        select(CardVersion)
        .where(CardVersion.card_id == card_id, CardVersion.is_latest.is_(True))
        .order_by(CardVersion.version_number.desc())
    )
    return session.exec(statement).first()


def get_card_image(session: Session, card_version_id: str) -> CardVersionImage | None:
    statement = select(CardVersionImage).where(CardVersionImage.card_version_id == card_version_id)
    return session.exec(statement).first()


def list_card_generations(session: Session, card_id: str) -> list[CardVersion]:
    statement = (
        select(CardVersion)
        .where(CardVersion.card_id == card_id)
        .order_by(CardVersion.version_number.desc())
    )
    return list(session.exec(statement))


def update_card(
    session: Session,
    *,
    card_id: str,
    name: str | None,
    type_line: str | None,
    mana_cost: str | None,
    rules_text: str | None,
) -> tuple[Card, CardVersion] | None:
    card = get_card(session, card_id)
    if card is None:
        return None

    version = get_latest_card_version(session, card.id)
    if version is None:
        return None

    if name is not None:
        card.label = name
        card.key = normalize_slug_key(name)
        version.name = name
    if type_line is not None:
        version.type_line = type_line
    if mana_cost is not None:
        version.mana_cost = mana_cost
    if rules_text is not None:
        version.rules_text = rules_text

    card.updated_at = now_utc()
    version.updated_at = now_utc()
    session.add(card)
    session.add(version)

    upsert_card_search(session, card_id=card.id, version=version)

    session.commit()
    session.refresh(card)
    session.refresh(version)
    return card, version


def apply_parsed_fields_to_version(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> None:
    version.name = normalized_fields.get("name", "")
    version.type_line = normalized_fields.get("type_line", "")
    version.mana_cost = normalized_fields.get("mana_cost", "")
    version.mana_symbols_json = json.dumps(extract_mana_symbols(normalized_fields))
    version.attack = to_int_or_none(normalized_fields.get("attack"))
    version.health = to_int_or_none(normalized_fields.get("health"))
    version.rules_text = normalized_fields.get("rules_text", "")
    version.confidence = float(confidence.get("overall", 0.0))


def upsert_card_search(session: Session, *, card_id: str, version: CardVersion) -> None:
    session.exec(
        text("DELETE FROM card_version_search WHERE card_id = :card_id"),
        params={"card_id": card_id},
    )
    session.exec(
        text(
            "INSERT INTO card_version_search(card_id, card_version_id, name, type_line, rules_text, mana_cost) "
            "VALUES (:card_id, :card_version_id, :name, :type_line, :rules_text, :mana_cost)"
        ),
        params={
            "card_id": card_id,
            "card_version_id": version.id,
            "name": version.name,
            "type_line": version.type_line,
            "rules_text": version.rules_text,
            "mana_cost": version.mana_cost,
        },
    )


