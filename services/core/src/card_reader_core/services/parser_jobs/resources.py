from __future__ import annotations

import logging

from card_reader_core.models import ImportJob
from card_reader_core.repositories.metadata import (
    list_detectable_symbols,
    list_keywords,
    list_tags,
    list_types,
)

from .types import JobOptions, ParserResources

logger = logging.getLogger(__name__)


class ParserJobContextLoader:
    def load_job_options(self, job: ImportJob) -> JobOptions:
        raw_options: dict[str, object] = {}
        if isinstance(job.options_json, dict):
            raw_options = job.options_json
        elif job.options_json:
            logger.warning("Ignoring invalid job options JSON. job_id=%s", job.id)

        return JobOptions(
            reparse_existing=self._to_bool(raw_options.get("reparse_existing"), default=True),
            keyword_keys=self._parse_keyword_keys(raw_options.get("keyword_keys")),
        )

    def load_parser_resources(self, options: JobOptions) -> ParserResources:
        return ParserResources(
            known_keywords=list_keywords(keys=options.keyword_keys),
            known_tags=list_tags(),
            known_types=list_types(),
            detectable_symbols=list_detectable_symbols(),
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
