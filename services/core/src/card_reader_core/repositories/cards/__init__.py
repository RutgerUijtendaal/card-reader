from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .images import list_latest_active_card_image_sources, resolve_image_file_path
from .queries import (
    get_card,
    get_card_image,
    get_latest_card_version,
    get_latest_card_list_rows_by_card_ids,
    list_card_generations,
    list_cards_for_content_version,
    get_card_list_rows_by_version_ids,
    list_cards,
    list_matching_card_candidates,
    list_matching_cards,
    list_filtered_latest_card_version_reparse_sources,
    list_latest_card_version_reparse_sources,
)
from .snapshots import (
    DEFAULT_FIELD_SOURCES,
    FIELD_SOURCE_AUTO,
    FIELD_SOURCE_MANUAL,
    METADATA_GROUP_NAMES,
    SCALAR_FIELD_NAMES,
    decode_field_sources,
    decode_parsed_snapshot,
)
from .types import (
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_TYPES_ASC,
    CARD_SORT_UPDATED_DESC,
    CARD_SORT_VALUES,
    DEFAULT_CARD_LIFECYCLE_FILTER,
    DEFAULT_CARD_PAGE_SIZE,
    CardFilterParams,
    CardImageSource,
    CardLifecycleFilter,
    CardListCandidate,
    CardListRow,
    CardSort,
    FieldSourcesPayload,
    LatestCardVersionReparseSource,
    PaginatedCardList,
    ParsedCardSaveResult,
    ParsedSnapshotPayload,
)
if TYPE_CHECKING:
    from .edits import promote_card_version, update_latest_card_version
    from .writes import apply_parsed_fields_to_version, save_parsed_card, save_parsed_card_result

_LAZY_MUTATION_EXPORTS = {
    "apply_parsed_fields_to_version": ".writes",
    "promote_card_version": ".edits",
    "save_parsed_card": ".writes",
    "save_parsed_card_result": ".writes",
    "update_latest_card_version": ".edits",
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY_MUTATION_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)

__all__ = [
    "CardListRow",
    "CardListCandidate",
    "CardFilterParams",
    "CardImageSource",
    "DEFAULT_FIELD_SOURCES",
    "DEFAULT_CARD_LIFECYCLE_FILTER",
    "DEFAULT_CARD_PAGE_SIZE",
    "FIELD_SOURCE_AUTO",
    "FIELD_SOURCE_MANUAL",
    "FieldSourcesPayload",
    "LatestCardVersionReparseSource",
    "METADATA_GROUP_NAMES",
    "PaginatedCardList",
    "ParsedCardSaveResult",
    "ParsedSnapshotPayload",
    "SCALAR_FIELD_NAMES",
    "apply_parsed_fields_to_version",
    "CARD_SORT_MANA_ASC",
    "CARD_SORT_MANA_DESC",
    "CARD_SORT_NAME_ASC",
    "CARD_SORT_TYPES_ASC",
    "CARD_SORT_UPDATED_DESC",
    "CARD_SORT_VALUES",
    "CardLifecycleFilter",
    "CardSort",
    "decode_field_sources",
    "decode_parsed_snapshot",
    "get_card",
    "get_card_image",
    "get_card_list_rows_by_version_ids",
    "get_latest_card_version",
    "get_latest_card_list_rows_by_card_ids",
    "list_card_generations",
    "list_cards_for_content_version",
    "list_cards",
    "list_matching_card_candidates",
    "list_matching_cards",
    "list_filtered_latest_card_version_reparse_sources",
    "list_latest_card_version_reparse_sources",
    "list_latest_active_card_image_sources",
    "promote_card_version",
    "resolve_image_file_path",
    "save_parsed_card",
    "save_parsed_card_result",
    "update_latest_card_version",
]
