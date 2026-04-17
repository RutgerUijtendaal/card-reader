from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlmodel import Session

import repositories as repositories
from models import ImportJobStatus
from parsers.card_parser import CardParser

logger = logging.getLogger(__name__)


class ImportProcessorService:
    def __init__(self, parser: CardParser) -> None:
        self._parser = parser

    def process_job(self, session: Session, job_id: str) -> None:
        job = repositories.fetch_job(session, job_id)
        if job is None:
            return

        options: dict[str, object] = {}
        if job.options_json:
            try:
                parsed_options = json.loads(job.options_json)
                if isinstance(parsed_options, dict):
                    options = parsed_options
            except json.JSONDecodeError:
                options = {}

        reparse_existing = self._to_bool(options.get("reparse_existing"), default=True)
        failed_items = 0

        repositories.mark_job_running(session, job)
        items = repositories.get_job_items(session, job.id)

        for item in items:
            if item.status != ImportJobStatus.queued:
                continue

            try:
                parsed = self._parser.parse(Path(item.source_file), job.template_id)
                repositories.save_parsed_card(
                    session,
                    item=item,
                    template_id=job.template_id,
                    checksum=parsed.checksum,
                    normalized_fields=parsed.normalized_fields,
                    confidence=parsed.confidence,
                    raw_ocr=parsed.raw_ocr,
                    reparse_existing=reparse_existing,
                )
            except Exception as exc:
                failed_items += 1
                repositories.mark_job_item_failed(session, item, str(exc))
                logger.exception(
                    "Failed to parse import item. job_id=%s item_id=%s source_file=%s",
                    job.id,
                    item.id,
                    item.source_file,
                )
            finally:
                repositories.bump_job_processed(session, job)

        if failed_items > 0:
            repositories.mark_job_failed(session, job)
            return
        repositories.mark_job_complete(session, job)

    def _to_bool(self, value: object, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return default
