from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

from sqlmodel import Session

import card_reader_core.repositories as repositories
from card_reader_core.models import ImportJobStatus
from ..parsers.card_parser import CardParser

logger = logging.getLogger(__name__)


class ImportProcessorService:
    def __init__(
        self,
        parser: CardParser,
    ) -> None:
        self._parser = parser

    def process_job(
        self,
        session: Session,
        job_id: str,
        *,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        job = repositories.fetch_job(session, job_id)
        if job is None:
            return
        stop_requested = should_stop or (lambda: False)

        options: dict[str, object] = {}
        if job.options_json:
            try:
                parsed_options = json.loads(job.options_json)
                if isinstance(parsed_options, dict):
                    options = parsed_options
            except json.JSONDecodeError:
                options = {}

        reparse_existing = self._to_bool(options.get("reparse_existing"), default=True)
        keyword_keys = self._parse_keyword_keys(options.get("keyword_keys"))
        known_keywords = repositories.list_keywords(session, keys=keyword_keys)
        detectable_symbols = repositories.list_detectable_symbols(session)
        failed_items = 0
        shutdown_requested = False

        repositories.mark_job_running(session, job)
        items = repositories.get_job_items(session, job.id)

        for item in items:
            if stop_requested():
                shutdown_requested = True
                logger.info("Parser shutdown requested; pausing job processing. job_id=%s", job.id)
                break
            if item.status != ImportJobStatus.queued:
                continue

            try:
                parsed = self._parser.parse(
                    Path(item.source_file),
                    job.template_id,
                    symbols=detectable_symbols,
                    known_keywords=known_keywords,
                )
                version = repositories.save_parsed_card(
                    session,
                    item=item,
                    template_id=job.template_id,
                    checksum=parsed.checksum,
                    normalized_fields=parsed.normalized_fields,
                    confidence=parsed.confidence,
                    raw_ocr=parsed.raw_ocr,
                    reparse_existing=reparse_existing,
                )
                repositories.replace_card_version_keywords(
                    session,
                    card_version_id=version.id,
                    keyword_ids=parsed.keyword_ids,
                )
                repositories.replace_card_version_symbols(
                    session,
                    card_version_id=version.id,
                    symbol_ids=parsed.symbol_ids,
                )
                tag_rows = repositories.upsert_tags_by_labels(session, parsed.tag_labels)
                type_rows = repositories.upsert_types_by_labels(session, parsed.type_labels)

                repositories.replace_card_version_tags(
                    session,
                    card_version_id=version.id,
                    tag_ids=[row.id for row in tag_rows],
                )
                repositories.replace_card_version_types(
                    session,
                    card_version_id=version.id,
                    type_ids=[row.id for row in type_rows],
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
        if shutdown_requested:
            repositories.mark_job_queued(session, job)
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

    def _parse_keyword_keys(self, value: object) -> set[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            return None

        keys: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            key = item.strip()
            if key:
                keys.add(key)
        return keys


