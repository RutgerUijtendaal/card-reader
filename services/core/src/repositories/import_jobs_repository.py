from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from models import ImportJob, ImportJobItem, ImportJobStatus, now_utc

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


