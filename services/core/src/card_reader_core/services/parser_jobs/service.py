from __future__ import annotations

import logging
from typing import Callable

from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus
from card_reader_core.repositories.import_jobs import (
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
from card_reader_core.repositories.metadata import (
    SuggestionCandidate,
)
from card_reader_core.repositories.cards import save_parsed_card
from card_reader_core.storage import resolve_storage_path
from .resources import ParserJobContextLoader
from .types import CardParserProtocol, ItemProcessingResult, JobOptions, ParserResources

logger = logging.getLogger(__name__)


class ImportProcessorService:
    def __init__(
        self,
        parser: CardParserProtocol,
        *,
        context_loader: ParserJobContextLoader | None = None,
    ) -> None:
        self._parser = parser
        self._context_loader = context_loader or ParserJobContextLoader()

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
        options = self._context_loader.load_job_options(job)
        resources = self._context_loader.load_parser_resources(options)
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
            tag_suggestions=[
                SuggestionCandidate(
                    display_value=row.display_value,
                    normalized_value=row.normalized_value,
                    source_text=row.source_text,
                    normalized_source_text=row.normalized_source_text,
                )
                for row in parsed.tag_suggestions
            ],
            type_suggestions=[
                SuggestionCandidate(
                    display_value=row.display_value,
                    normalized_value=row.normalized_value,
                    source_text=row.source_text,
                    normalized_source_text=row.normalized_source_text,
                )
                for row in parsed.type_suggestions
            ],
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
