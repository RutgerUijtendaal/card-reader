from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "SUPPORTED_IMAGE_SUFFIXES": ".import_jobs_repository",
    "collect_supported_files": ".import_jobs_repository",
    "list_import_jobs": ".import_jobs_repository",
    "create_import_job": ".import_jobs_repository",
    "mark_job_running": ".import_jobs_repository",
    "mark_job_queued": ".import_jobs_repository",
    "mark_job_complete": ".import_jobs_repository",
    "mark_job_failed": ".import_jobs_repository",
    "bump_job_processed": ".import_jobs_repository",
    "fetch_job": ".import_jobs_repository",
    "fetch_items_for_job": ".import_jobs_repository",
    "get_next_queued_job": ".import_jobs_repository",
    "get_job_items": ".import_jobs_repository",
    "mark_job_item_failed": ".import_jobs_repository",
    "requeue_running_import_jobs": ".import_jobs_repository",
    "save_parsed_card": ".cards_repository",
    "list_cards": ".cards_repository",
    "get_card": ".cards_repository",
    "get_latest_card_version": ".cards_repository",
    "get_card_image": ".cards_repository",
    "get_parse_result": ".cards_repository",
    "list_card_generations": ".cards_repository",
    "update_card": ".cards_repository",
    "update_latest_card_version": ".cards_repository",
    "decode_field_sources": ".cards_repository",
    "decode_parsed_snapshot": ".cards_repository",
    "export_cards_csv": ".exports_repository",
    "normalize_slug_key": ".helpers",
    "list_keywords": ".metadata_repository",
    "list_tags": ".metadata_repository",
    "list_symbols": ".metadata_repository",
    "list_types": ".metadata_repository",
    "list_detectable_symbols": ".metadata_repository",
    "get_keyword": ".metadata_repository",
    "get_tag": ".metadata_repository",
    "get_symbol": ".metadata_repository",
    "get_type": ".metadata_repository",
    "keyword_key_exists": ".metadata_repository",
    "tag_key_exists": ".metadata_repository",
    "symbol_key_exists": ".metadata_repository",
    "type_key_exists": ".metadata_repository",
    "create_keyword": ".metadata_repository",
    "create_tag": ".metadata_repository",
    "create_symbol": ".metadata_repository",
    "create_type": ".metadata_repository",
    "update_keyword": ".metadata_repository",
    "update_tag": ".metadata_repository",
    "update_symbol": ".metadata_repository",
    "update_type": ".metadata_repository",
    "delete_keyword": ".metadata_repository",
    "delete_tag": ".metadata_repository",
    "delete_symbol": ".metadata_repository",
    "delete_type": ".metadata_repository",
    "replace_card_version_keywords": ".metadata_repository",
    "replace_card_version_symbols": ".metadata_repository",
    "replace_card_version_tags": ".metadata_repository",
    "replace_card_version_types": ".metadata_repository",
    "get_keywords_for_card_version": ".metadata_repository",
    "get_tags_for_card_version": ".metadata_repository",
    "get_symbols_for_card_version": ".metadata_repository",
    "get_types_for_card_version": ".metadata_repository",
    "list_templates": ".templates_repository",
    "get_template": ".templates_repository",
    "get_template_by_key": ".templates_repository",
    "template_key_exists": ".templates_repository",
    "create_template": ".templates_repository",
    "update_template": ".templates_repository",
    "delete_template": ".templates_repository",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
