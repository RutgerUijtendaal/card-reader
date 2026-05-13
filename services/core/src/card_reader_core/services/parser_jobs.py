from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus, Keyword, Symbol, Tag, Type
from card_reader_core.repositories.import_jobs_repository import (
    bump_job_processed,
    fetch_job,
    fetch_items_for_job,
    mark_job_cancelled,
    mark_job_complete,
    mark_job_failed,
    mark_job_item_failed,
    mark_job_item_running,
    mark_job_queued,
    mark_job_running,
)
from card_reader_core.repositories.metadata_repository import (
    list_detectable_symbols,
    list_keywords,
    list_tags,
    list_types,
)
from card_reader_core.repositories.cards_repository import save_parsed_card
from card_reader_core.storage import resolve_storage_path

logger = logging.getLogger(__name__)


class CardParserProtocol(Protocol):
    def parse(
        self,
        image_path: Path,
        template_id: str,
        *,
        symbols: list[Symbol],
        known_keywords: list[Keyword],
        known_tags: list[Tag],
        known_types: list[Type],
    ) -> Any:
        pass


@dataclass(frozen=True)
class JobOptions:
    reparse_existing: bool
    keyword_keys: set[str] | None


@dataclass(frozen=True)
class ParserResources:
    known_keywords: list[Keyword]
    known_tags: list[Tag]
    known_types: list[Type]
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
    def __init__(self, parser: CardParserProtocol) -> None:
        self._parser = parser

    def process_job(
        self,
        job_id: str,
        *,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        job = fetch_job(job_id)
        if job is None:
            logger.warning("process_job called for missing job. job_id=%s", job_id)
            return

        stop_requested = should_stop or (lambda: False)
        options = self._load_job_options(job)
        resources = self._load_parser_resources(options)
        failed_items = 0
        shutdown_requested = False
        cancel_requested = False

        mark_job_running(job)
        for item in fetch_items_for_job(job.id):
            current_job = fetch_job(job.id)
            if current_job is None:
                logger.warning("Stopping processing for missing job during run. job_id=%s", job.id)
                return
            if current_job.status in {ImportJobStatus.canceling, ImportJobStatus.cancelled}:
                cancel_requested = True
                break
            if stop_requested():
                shutdown_requested = True
                break
            item.refresh_from_db(fields=["status", "error_message", "updated_at"])
            if item.status != ImportJobStatus.queued:
                continue
            mark_job_item_running(item)
            failed_items += self._process_item_with_failure_tracking(job, item, options, resources)
            bump_job_processed(job)
            current_job = fetch_job(job.id)
            if current_job is not None and current_job.status == ImportJobStatus.canceling:
                cancel_requested = True
                break

        if cancel_requested:
            mark_job_cancelled(job)
        elif failed_items > 0:
            mark_job_failed(job)
        elif shutdown_requested:
            mark_job_queued(job)
        else:
            mark_job_complete(job)

    def _process_item_with_failure_tracking(
        self,
        job: ImportJob,
        item: ImportJobItem,
        options: JobOptions,
        resources: ParserResources,
        ) -> int:
        try:
            result = self._process_queued_item(job, item, options, resources)
            self._log_item_processed(job, item, result)
            return 0
        except Exception as exc:
            mark_job_item_failed(item, str(exc))
            logger.exception(
                "Failed to parse import item. job_id=%s item_id=%s source_file=%s",
                job.id,
                item.id,
                item.source_file,
            )
            return 1

    def _process_queued_item(
        self,
        job: ImportJob,
        item: ImportJobItem,
        options: JobOptions,
        resources: ParserResources,
    ) -> ItemProcessingResult:
        parsed = self._parser.parse(
            resolve_storage_path(item.source_file),
            job.template_id,
            symbols=resources.detectable_symbols,
            known_keywords=resources.known_keywords,
            known_tags=resources.known_tags,
            known_types=resources.known_types,
        )
        save_parsed_card(
            item=item,
            template_id=job.template_id,
            checksum=parsed.checksum,
            normalized_fields=parsed.normalized_fields,
            confidence=parsed.confidence,
            raw_ocr=parsed.raw_ocr,
            keyword_ids=parsed.keyword_ids,
            tag_ids=parsed.tag_ids,
            type_ids=parsed.type_ids,
            symbol_ids=parsed.symbol_ids,
            reparse_existing=options.reparse_existing,
        )
        tag_count = len(parsed.tag_ids)
        type_count = len(parsed.type_ids)
        return ItemProcessingResult(
            checksum=parsed.checksum,
            confidence=float(parsed.confidence.get("overall", 0.0)),
            keyword_count=len(parsed.keyword_ids),
            symbol_count=len(parsed.symbol_ids),
            tag_count=tag_count,
            type_count=type_count,
        )

    def _load_job_options(self, job: ImportJob) -> JobOptions:
        raw_options: dict[str, object] = {}
        if isinstance(job.options_json, dict):
            raw_options = job.options_json
        elif job.options_json:
            logger.warning("Ignoring invalid job options JSON. job_id=%s", job.id)

        return JobOptions(
            reparse_existing=self._to_bool(raw_options.get("reparse_existing"), default=True),
            keyword_keys=self._parse_keyword_keys(raw_options.get("keyword_keys")),
        )

    def _load_parser_resources(self, options: JobOptions) -> ParserResources:
        return ParserResources(
            known_keywords=list_keywords(keys=options.keyword_keys),
            known_tags=list_tags(),
            known_types=list_types(),
            detectable_symbols=list_detectable_symbols(),
        )

    def _log_item_processed(
        self,
        job: ImportJob,
        item: ImportJobItem,
        result: ItemProcessingResult,
    ) -> None:
        logger.info(
            "Import item processed. job_id=%s item_id=%s checksum=%s overall_conf=%.3f",
            job.id,
            item.id,
            result.checksum,
            result.confidence,
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
        if not isinstance(value, list):
            return None
        return {item.strip() for item in value if isinstance(item, str) and item.strip()}
