from __future__ import annotations

import logging
from typing import Callable, TypeVar, cast

from card_reader_core.models import (
    CardFaction,
    CardPool,
    CardRole,
    ImportJob,
    ImportJobItem,
    ImportJobStatus,
    Symbol,
    Tag,
    Type,
)
from card_reader_core.metadata import ManaFamily
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
from card_reader_core.services.cards import save_parsed_card_with_notifications
from card_reader_core.services.classification_rules import ClassificationRuleService
from card_reader_core.services.imports import (
    CardClassificationInput,
    CardClassificationMode,
    DetectedClassificationSource,
    classify_import_card,
)
from card_reader_core.storage import resolve_storage_path
from .resources import ParserJobContextLoader
from .types import CardParserProtocol, ItemProcessingResult, JobOptions, ParserResources

logger = logging.getLogger(__name__)
_MetadataSource = TypeVar("_MetadataSource", Tag, Type, Symbol)


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
            item.refresh_from_db(fields=["status", "error_message", "updated_at"])
            if item.status == ImportJobStatus.completed:
                logger.exception(
                    "Post-success import work failed without changing completed state. "
                    "job_id=%s item_id=%s",
                    job.id,
                    item.id,
                )
                return 0
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
        template_id = job.template.key
        snapshot = cast(dict[str, object], job.classification_rule_snapshot_json)
        frozen_tags, frozen_types, frozen_symbols = (
            ClassificationRuleService().detector_sources_from_snapshot(
                snapshot,
                card_pool=cast(CardPool, job.card_pool),
            )
        )
        detection_tags = _merge_metadata_sources(resources.known_tags, frozen_tags)
        detection_types = _merge_metadata_sources(resources.known_types, frozen_types)
        snapshot_symbols = _merge_metadata_sources(
            resources.detectable_symbols, frozen_symbols
        )
        detection_symbols = [
            symbol
            for symbol in snapshot_symbols
            if symbol.enabled and symbol.detector_type == "template"
        ]
        parsed = self._parser.parse(
            resolve_storage_path(item.source_file),
            template_id,
            card_pool=cast(CardPool, job.card_pool),
            symbols=detection_symbols,
            known_keywords=resources.known_keywords,
            known_tags=detection_tags,
            known_types=detection_types,
        )
        tag_keys_by_id = {tag.id: tag.key for tag in detection_tags}
        type_keys_by_id = {type_row.id: type_row.key for type_row in detection_types}
        live_tag_ids = {tag.id for tag in resources.known_tags}
        live_type_ids = {type_row.id for type_row in resources.known_types}
        symbol_keys_by_id = {symbol.id: symbol.key for symbol in detection_symbols}
        matched_tags = tuple(
            DetectedClassificationSource(id=tag_id, key=tag_keys_by_id[tag_id])
            for tag_id in parsed.tag_ids
            if tag_id in tag_keys_by_id
        )
        matched_types = tuple(
            DetectedClassificationSource(id=type_id, key=type_keys_by_id[type_id])
            for type_id in parsed.type_ids
            if type_id in type_keys_by_id
        )
        matched_symbols = tuple(
            DetectedClassificationSource(id=symbol_id, key=symbol_keys_by_id[symbol_id])
            for symbol_id in parsed.symbol_ids
            if symbol_id in symbol_keys_by_id
        )
        classification = classify_import_card(
            CardClassificationInput(
                card_pool=cast(CardPool, job.card_pool),
                role_mode=cast(CardClassificationMode, job.card_role_mode),
                override_roles=cast(tuple[CardRole, ...], tuple(job.card_role_override_json)),
                faction_mode=cast(CardClassificationMode, job.card_faction_mode),
                override_factions=cast(
                    tuple[CardFaction, ...], tuple(job.card_faction_override_json)
                ),
                mana_family_mode=cast(
                    CardClassificationMode, job.card_mana_family_mode
                ),
                override_mana_families=cast(
                    tuple[ManaFamily, ...], tuple(job.card_mana_family_override_json)
                ),
                rule_snapshot=snapshot,
                matched_tags=matched_tags,
                matched_types=matched_types,
                matched_symbols=matched_symbols,
            )
        )
        save_parsed_card_with_notifications(
            item=item,
            template_id=template_id,
            checksum=parsed.checksum,
            normalized_fields=parsed.normalized_fields,
            confidence=parsed.confidence,
            raw_ocr=parsed.raw_ocr,
            keyword_ids=parsed.keyword_ids,
            tag_ids=[tag_id for tag_id in parsed.tag_ids if tag_id in live_tag_ids],
            type_ids=[type_id for type_id in parsed.type_ids if type_id in live_type_ids],
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
            card_pool=classification.card_pool,
            resolved_card_roles=classification.roles,
            resolved_card_factions=classification.factions,
            resolved_card_mana_families=classification.mana_families,
            classification_evidence=classification.evidence,
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


def _merge_metadata_sources(
    live_sources: list[_MetadataSource],
    frozen_sources: list[_MetadataSource],
) -> list[_MetadataSource]:
    frozen_by_id = {source.id: source for source in frozen_sources}
    merged = [source for source in live_sources if source.id not in frozen_by_id]
    merged.extend(frozen_sources)
    return sorted(merged, key=lambda source: (source.key, source.id))
