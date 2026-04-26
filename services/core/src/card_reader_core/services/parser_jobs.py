from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import card_reader_core.repositories as repositories
from card_reader_core.models import ImportJob, ImportJobItem, ImportJobStatus, Keyword, Symbol

logger = logging.getLogger(__name__)


class CardParserProtocol(Protocol):
    def parse(
        self,
        image_path: Path,
        template_id: str,
        *,
        symbols: list[Symbol],
        known_keywords: list[Keyword],
    ) -> Any:
        pass


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
    def __init__(self, parser: CardParserProtocol) -> None:
        self._parser = parser

    def process_job(
        self,
        _session: object,
        job_id: str,
        *,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        job = repositories.fetch_job(None, job_id)
        if job is None:
            logger.warning("process_job called for missing job. job_id=%s", job_id)
            return

        stop_requested = should_stop or (lambda: False)
        options = self._load_job_options(job)
        resources = self._load_parser_resources(options)
        failed_items = 0
        shutdown_requested = False

        repositories.mark_job_running(None, job)
        for item in repositories.get_job_items(None, job.id):
            if stop_requested():
                shutdown_requested = True
                break
            if item.status != ImportJobStatus.queued:
                continue
            failed_items += self._process_item_with_failure_tracking(job, item, options, resources)
            repositories.bump_job_processed(None, job)

        if failed_items > 0:
            repositories.mark_job_failed(None, job)
        elif shutdown_requested:
            repositories.mark_job_queued(None, job)
        else:
            repositories.mark_job_complete(None, job)

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
            repositories.mark_job_item_failed(None, item, str(exc))
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
            Path(item.source_file),
            job.template_id,
            symbols=resources.detectable_symbols,
            known_keywords=resources.known_keywords,
        )
        version = repositories.save_parsed_card(
            None,
            item=item,
            template_id=job.template_id,
            checksum=parsed.checksum,
            normalized_fields=parsed.normalized_fields,
            confidence=parsed.confidence,
            raw_ocr=parsed.raw_ocr,
            reparse_existing=options.reparse_existing,
        )
        tag_count, type_count = self._replace_metadata_links(version.id, parsed)
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

    def _load_parser_resources(self, options: JobOptions) -> ParserResources:
        return ParserResources(
            known_keywords=repositories.list_keywords(None, keys=options.keyword_keys),
            detectable_symbols=repositories.list_detectable_symbols(None),
        )

    def _replace_metadata_links(self, card_version_id: str, parsed: Any) -> tuple[int, int]:
        repositories.replace_card_version_keywords(
            None,
            card_version_id=card_version_id,
            keyword_ids=parsed.keyword_ids,
        )
        repositories.replace_card_version_symbols(
            None,
            card_version_id=card_version_id,
            symbol_ids=parsed.symbol_ids,
        )
        tag_rows = repositories.upsert_tags_by_labels(None, parsed.tag_labels)
        type_rows = repositories.upsert_types_by_labels(None, parsed.type_labels)
        repositories.replace_card_version_tags(
            None,
            card_version_id=card_version_id,
            tag_ids=[row.id for row in tag_rows],
        )
        repositories.replace_card_version_types(
            None,
            card_version_id=card_version_id,
            type_ids=[row.id for row in type_rows],
        )
        return len(tag_rows), len(type_rows)

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
