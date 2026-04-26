from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlmodel import Session

import card_reader_core.repositories as repositories
from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus, Keyword, Symbol
from ..parsers.card_parser import CardParser
from ..parsers.types import ParsedCard

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobOptions:
    reparse_existing: bool
    keyword_keys: set[str] | None


@dataclass(frozen=True)
class ParserResources:
    known_keywords: list[Keyword]
    detectable_symbols: list[Symbol]


@dataclass(frozen=True)
class ItemProcessingResult:
    checksum: str
    confidence: float
    keyword_count: int
    symbol_count: int
    tag_count: int
    type_count: int


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

        options = self._load_job_options(job)
        resources = self._load_parser_resources(session, options)
        logger.info(
            "Import job processing started. job_id=%s template_id=%s total_items=%s reparse_existing=%s detectable_symbols=%s known_keywords=%s",
            job.id,
            job.template_id,
            job.total_items,
            options.reparse_existing,
            len(resources.detectable_symbols),
            len(resources.known_keywords),
        )

        failed_items = 0
        shutdown_requested = False

        repositories.mark_job_running(session, job)
        items = repositories.get_job_items(session, job.id)

        for item in items:
            if stop_requested():
                shutdown_requested = True
                break
            if item.status != ImportJobStatus.queued:
                continue

            try:
                result = self._process_queued_item(session, job, item, options, resources)
                self._log_item_processed(job, item, result)
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
            self._fail_job(session, job, failed_items)
            return
        if shutdown_requested:
            self._pause_job(session, job)
            return

        self._complete_job(session, job)

    def _load_job_options(self, job: ImportJob) -> JobOptions:
        raw_options: dict[str, object] = {}
        if job.options_json:
            try:
                parsed_options = json.loads(job.options_json)
                if isinstance(parsed_options, dict):
                    raw_options = parsed_options
            except json.JSONDecodeError:
                logger.warning("Ignoring invalid job options JSON. job_id=%s", job.id)

        return JobOptions(
            reparse_existing=self._to_bool(raw_options.get("reparse_existing"), default=True),
            keyword_keys=self._parse_keyword_keys(raw_options.get("keyword_keys")),
        )

    def _load_parser_resources(self, session: Session, options: JobOptions) -> ParserResources:
        return ParserResources(
            known_keywords=repositories.list_keywords(session, keys=options.keyword_keys),
            detectable_symbols=repositories.list_detectable_symbols(session),
        )

    def _process_queued_item(
        self,
        session: Session,
        job: ImportJob,
        item: ImportJobItem,
        options: JobOptions,
        resources: ParserResources,
    ) -> ItemProcessingResult:
        parsed = self._parse_item(job, item, resources)
        version = repositories.save_parsed_card(
            session,
            item=item,
            template_id=job.template_id,
            checksum=parsed.checksum,
            normalized_fields=parsed.normalized_fields,
            confidence=parsed.confidence,
            raw_ocr=parsed.raw_ocr,
            reparse_existing=options.reparse_existing,
        )
        tag_count, type_count = self._replace_metadata_links(session, version.id, parsed)
        return ItemProcessingResult(
            checksum=parsed.checksum,
            confidence=float(parsed.confidence.get("overall", 0.0)),
            keyword_count=len(parsed.keyword_ids),
            symbol_count=len(parsed.symbol_ids),
            tag_count=tag_count,
            type_count=type_count,
        )

    def _parse_item(
        self,
        job: ImportJob,
        item: ImportJobItem,
        resources: ParserResources,
    ) -> ParsedCard:
        return self._parser.parse(
            Path(item.source_file),
            job.template_id,
            symbols=resources.detectable_symbols,
            known_keywords=resources.known_keywords,
        )

    def _replace_metadata_links(
        self,
        session: Session,
        card_version_id: str,
        parsed: ParsedCard,
    ) -> tuple[int, int]:
        repositories.replace_card_version_keywords(
            session,
            card_version_id=card_version_id,
            keyword_ids=parsed.keyword_ids,
        )
        repositories.replace_card_version_symbols(
            session,
            card_version_id=card_version_id,
            symbol_ids=parsed.symbol_ids,
        )
        tag_rows = repositories.upsert_tags_by_labels(session, parsed.tag_labels)
        type_rows = repositories.upsert_types_by_labels(session, parsed.type_labels)

        repositories.replace_card_version_tags(
            session,
            card_version_id=card_version_id,
            tag_ids=[row.id for row in tag_rows],
        )
        repositories.replace_card_version_types(
            session,
            card_version_id=card_version_id,
            type_ids=[row.id for row in type_rows],
        )
        return len(tag_rows), len(type_rows)

    def _pause_job(self, session: Session, job: ImportJob) -> None:
        repositories.mark_job_queued(session, job)
        logger.info(
            "Import job paused. job_id=%s processed_items=%s total_items=%s",
            job.id,
            job.processed_items,
            job.total_items,
        )

    def _fail_job(self, session: Session, job: ImportJob, failed_items: int) -> None:
        repositories.mark_job_failed(session, job)
        logger.warning(
            "Import job failed. job_id=%s failed_items=%s processed_items=%s total_items=%s",
            job.id,
            failed_items,
            job.processed_items,
            job.total_items,
        )

    def _complete_job(self, session: Session, job: ImportJob) -> None:
        repositories.mark_job_complete(session, job)
        logger.info(
            "Import job completed. job_id=%s processed_items=%s total_items=%s",
            job.id,
            job.processed_items,
            job.total_items,
        )

    def _log_item_processed(
        self,
        job: ImportJob,
        item: ImportJobItem,
        result: ItemProcessingResult,
    ) -> None:
        logger.info(
            "Import item processed. job_id=%s item_id=%s checksum=%s overall_conf=%.3f keywords=%s symbols=%s tags=%s types=%s",
            job.id,
            item.id,
            result.checksum,
            result.confidence,
            result.keyword_count,
            result.symbol_count,
            result.tag_count,
            result.type_count,
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


