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
            logger.warning("process_job called for missing job. job_id=%s", job_id)
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
        logger.info(
            "Starting job processing. job_id=%s template_id=%s total_items=%s reparse_existing=%s detectable_symbols=%s known_keywords=%s",
            job.id,
            job.template_id,
            job.total_items,
            reparse_existing,
            len(detectable_symbols),
            len(known_keywords),
        )
        failed_items = 0
        shutdown_requested = False

        repositories.mark_job_running(session, job)
        items = repositories.get_job_items(session, job.id)
        logger.info("Loaded job items. job_id=%s item_count=%s", job.id, len(items))

        for item in items:
            if stop_requested():
                shutdown_requested = True
                logger.info("Parser shutdown requested; pausing job processing. job_id=%s", job.id)
                break
            if item.status != ImportJobStatus.queued:
                logger.info(
                    "Skipping non-queued item. job_id=%s item_id=%s status=%s",
                    job.id,
                    item.id,
                    item.status,
                )
                continue

            try:
                logger.info(
                    "Processing job item. job_id=%s item_id=%s source_file=%s",
                    job.id,
                    item.id,
                    item.source_file,
                )
                parsed = self._parser.parse(
                    Path(item.source_file),
                    job.template_id,
                    symbols=detectable_symbols,
                    known_keywords=known_keywords,
                )
                logger.info(
                    "Parse completed. job_id=%s item_id=%s checksum=%s overall_conf=%.3f",
                    job.id,
                    item.id,
                    parsed.checksum,
                    float(parsed.confidence.get("overall", 0.0)),
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
                logger.info(
                    "Card version saved. job_id=%s item_id=%s card_version_id=%s version_number=%s",
                    job.id,
                    item.id,
                    version.id,
                    version.version_number,
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
                logger.info(
                    "Metadata links updated. job_id=%s item_id=%s keywords=%s symbols=%s tags=%s types=%s",
                    job.id,
                    item.id,
                    len(parsed.keyword_ids),
                    len(parsed.symbol_ids),
                    len(tag_rows),
                    len(type_rows),
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
                logger.info(
                    "Job progress bumped. job_id=%s processed_items=%s/%s",
                    job.id,
                    job.processed_items,
                    job.total_items,
                )

        if failed_items > 0:
            repositories.mark_job_failed(session, job)
            logger.warning(
                "Job marked failed. job_id=%s failed_items=%s processed_items=%s total_items=%s",
                job.id,
                failed_items,
                job.processed_items,
                job.total_items,
            )
            return
        if shutdown_requested:
            repositories.mark_job_queued(session, job)
            logger.info(
                "Job re-queued due to shutdown request. job_id=%s processed_items=%s total_items=%s",
                job.id,
                job.processed_items,
                job.total_items,
            )
            return
        repositories.mark_job_complete(session, job)
        logger.info(
            "Job completed successfully. job_id=%s processed_items=%s total_items=%s",
            job.id,
            job.processed_items,
            job.total_items,
        )

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


