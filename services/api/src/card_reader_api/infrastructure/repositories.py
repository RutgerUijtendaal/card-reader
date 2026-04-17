from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, select

from card_reader_api.infrastructure.models import (
    Card,
    CardImage,
    ImportJob,
    ImportJobItem,
    ImportJobStatus,
    ParseResult,
    now_utc,
)
from card_reader_api.infrastructure.storage import store_image

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def list_import_jobs(session: Session) -> list[ImportJob]:
    statement = select(ImportJob).order_by(ImportJob.created_at.desc())
    return list(session.exec(statement))


def create_import_job(
    session: Session,
    *,
    source_path: Path,
    template_id: str,
    options: dict[str, object],
) -> ImportJob:
    files = collect_supported_files(source_path)
    job = ImportJob(
        source_path=str(source_path),
        template_id=template_id,
        options_json=json.dumps(options),
        total_items=len(files),
        processed_items=0,
    )
    session.add(job)
    session.flush()

    for image_file in files:
        session.add(
            ImportJobItem(
                job_id=job.id,
                source_file=str(image_file),
                status=ImportJobStatus.queued,
            )
        )

    session.commit()
    session.refresh(job)
    return job


def collect_supported_files(source_path: Path) -> list[Path]:
    if source_path.is_file():
        return [source_path] if source_path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES else []

    if source_path.is_dir():
        return sorted(
            [
                path
                for path in source_path.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
            ]
        )

    return []


def mark_job_running(session: Session, job: ImportJob) -> None:
    job.status = ImportJobStatus.running
    job.updated_at = now_utc()
    session.add(job)
    session.commit()


def mark_job_complete(session: Session, job: ImportJob) -> None:
    job.status = ImportJobStatus.completed
    job.updated_at = now_utc()
    session.add(job)
    session.commit()


def mark_job_failed(session: Session, job: ImportJob) -> None:
    job.status = ImportJobStatus.failed
    job.updated_at = now_utc()
    session.add(job)
    session.commit()


def bump_job_processed(session: Session, job: ImportJob) -> None:
    job.processed_items += 1
    job.updated_at = now_utc()
    session.add(job)
    session.commit()


def fetch_job(session: Session, job_id: str) -> ImportJob | None:
    return session.get(ImportJob, job_id)


def fetch_items_for_job(session: Session, job_id: str) -> list[ImportJobItem]:
    statement = select(ImportJobItem).where(ImportJobItem.job_id == job_id)
    return list(session.exec(statement))


def get_next_queued_job(session: Session) -> ImportJob | None:
    statement = (
        select(ImportJob)
        .where(ImportJob.status == ImportJobStatus.queued)
        .order_by(ImportJob.created_at)
    )
    return session.exec(statement).first()


def get_job_items(session: Session, job_id: str) -> list[ImportJobItem]:
    statement = select(ImportJobItem).where(ImportJobItem.job_id == job_id)
    return list(session.exec(statement))


def mark_job_item_failed(session: Session, item: ImportJobItem, error_message: str) -> None:
    item.status = ImportJobStatus.failed
    item.error_message = error_message[:2000]
    item.updated_at = now_utc()
    session.add(item)
    session.commit()


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
) -> Card:
    existing = session.exec(select(Card).where(Card.image_hash == checksum)).first()
    if existing:
        if reparse_existing:
            _apply_parsed_fields_to_card(
                existing,
                normalized_fields=normalized_fields,
                confidence=confidence,
            )
            parse_result = ParseResult(
                card_id=existing.id,
                raw_ocr_json=json.dumps(raw_ocr),
                normalized_fields_json=json.dumps(normalized_fields),
                confidence_json=json.dumps(confidence),
            )
            session.add(parse_result)
            session.flush()
            existing.parse_result_id = parse_result.id
            existing.updated_at = now_utc()
            session.add(existing)
            _upsert_card_search(session, existing)

        item.status = ImportJobStatus.completed
        item.error_message = None
        item.updated_at = now_utc()
        session.add(item)
        session.commit()
        session.refresh(existing)
        return existing

    source_file_path = Path(item.source_file)
    stored_path = store_image(source_file_path, checksum)

    card = Card(
        template_id=template_id,
        image_hash=checksum,
        name=normalized_fields.get("name", ""),
        type_line=normalized_fields.get("type_line", ""),
        mana_cost=normalized_fields.get("mana_cost", ""),
        rules_text=normalized_fields.get("rules_text", ""),
        confidence=float(confidence.get("overall", 0.0)),
    )
    session.add(card)
    session.flush()

    parse_result = ParseResult(
        card_id=card.id,
        raw_ocr_json=json.dumps(raw_ocr),
        normalized_fields_json=json.dumps(normalized_fields),
        confidence_json=json.dumps(confidence),
    )
    session.add(parse_result)
    session.flush()

    card.parse_result_id = parse_result.id
    session.add(card)

    image_record = CardImage(
        card_id=card.id,
        source_file=item.source_file,
        stored_path=str(stored_path),
        checksum=checksum,
    )
    session.add(image_record)

    item.status = ImportJobStatus.completed
    item.updated_at = now_utc()
    session.add(item)

    session.commit()
    session.refresh(card)

    _upsert_card_search(session, card)
    session.commit()
    return card


def list_cards(
    session: Session,
    *,
    query: str | None,
    max_confidence: float | None,
) -> list[Card]:
    statement = select(Card)
    if max_confidence is not None:
        statement = statement.where(Card.confidence <= max_confidence)

    if query:
        rows = session.exec(
            text("SELECT card_id FROM card_search WHERE card_search MATCH :query"),
            params={"query": query},
        )
        card_ids = [row[0] for row in rows]
        if not card_ids:
            return []
        statement = statement.where(Card.id.in_(card_ids))

    statement = statement.order_by(Card.updated_at.desc())
    return list(session.exec(statement))


def get_card(session: Session, card_id: str) -> Card | None:
    return session.get(Card, card_id)


def get_card_image(session: Session, card_id: str) -> CardImage | None:
    statement = select(CardImage).where(CardImage.card_id == card_id)
    return session.exec(statement).first()


def update_card(
    session: Session,
    *,
    card_id: str,
    name: str | None,
    type_line: str | None,
    mana_cost: str | None,
    rules_text: str | None,
) -> Card | None:
    card = get_card(session, card_id)
    if card is None:
        return None

    if name is not None:
        card.name = name
    if type_line is not None:
        card.type_line = type_line
    if mana_cost is not None:
        card.mana_cost = mana_cost
    if rules_text is not None:
        card.rules_text = rules_text

    card.updated_at = now_utc()
    session.add(card)
    session.commit()
    session.refresh(card)

    _upsert_card_search(session, card)
    session.commit()
    return card


def export_cards_csv(session: Session, *, query: str | None) -> str:
    cards = list_cards(session, query=query, max_confidence=None)
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=["id", "name", "type_line", "mana_cost", "rules_text", "template_id", "confidence"],
    )
    writer.writeheader()
    for card in cards:
        writer.writerow(
            {
                "id": card.id,
                "name": card.name,
                "type_line": card.type_line,
                "mana_cost": card.mana_cost,
                "rules_text": card.rules_text,
                "template_id": card.template_id,
                "confidence": card.confidence,
            }
        )
    return stream.getvalue()


def _apply_parsed_fields_to_card(
    card: Card,
    *,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> None:
    card.name = normalized_fields.get("name", "")
    card.type_line = normalized_fields.get("type_line", "")
    card.mana_cost = normalized_fields.get("mana_cost", "")
    card.rules_text = normalized_fields.get("rules_text", "")
    card.confidence = float(confidence.get("overall", 0.0))


def _upsert_card_search(session: Session, card: Card) -> None:
    session.exec(
        text("DELETE FROM card_search WHERE card_id = :card_id"),
        params={"card_id": card.id},
    )
    session.exec(
        text(
            "INSERT INTO card_search(card_id, name, type_line, rules_text, mana_cost) "
            "VALUES (:card_id, :name, :type_line, :rules_text, :mana_cost)"
        ),
        params={
            "card_id": card.id,
            "name": card.name,
            "type_line": card.type_line,
            "rules_text": card.rules_text,
            "mana_cost": card.mana_cost,
        },
    )
