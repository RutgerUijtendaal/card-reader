from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .images import (
    list_latest_active_card_image_sources,
    resolve_image_file_path,
    select_usable_card_image,
)
from .classification import set_card_mana_families
from .identity import (
    change_card_identity,
    conflicting_card_id_for_key,
    create_card_identity,
    ensure_card_alias,
    lock_card_identity_pools,
    resolve_card_by_name_key,
)
from .queries import (
    get_card,
    get_card_image,
    get_latest_card_version,
    get_latest_card_list_rows_by_card_ids,
    list_card_generations,
    list_cards_for_content_version,
    get_card_list_rows_by_version_ids,
    list_cards,
    list_cards_across_pools,
    list_default_grouped_card_references,
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
from .sorting import build_type_sort_lookup, card_default_sort_key, card_type_sort_key
from .types import (
    CARD_SORT_DEFAULT,
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_MANA_TYPE_ASC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_TYPES_ASC,
    CARD_SORT_UPDATED_DESC,
    CARD_SORT_VALUES,
    DEFAULT_CARD_LIFECYCLE_FILTER,
    DEFAULT_CARD_PAGE_SIZE,
    CardFilterParams,
    CardIdentityConflict,
    CardImageSource,
    CardLifecycleFilter,
    CardListCandidate,
    CardListRow,
    CardSort,
    FieldSourcesPayload,
    GroupedCardListReference,
    LatestCardVersionReparseSource,
    PaginatedCardList,
    PaginatedGroupedCardList,
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
    "CardIdentityConflict",
    "DEFAULT_FIELD_SOURCES",
    "DEFAULT_CARD_LIFECYCLE_FILTER",
    "DEFAULT_CARD_PAGE_SIZE",
    "FIELD_SOURCE_AUTO",
    "FIELD_SOURCE_MANUAL",
    "FieldSourcesPayload",
    "GroupedCardListReference",
    "LatestCardVersionReparseSource",
    "METADATA_GROUP_NAMES",
    "PaginatedCardList",
    "PaginatedGroupedCardList",
    "ParsedCardSaveResult",
    "ParsedSnapshotPayload",
    "SCALAR_FIELD_NAMES",
    "apply_parsed_fields_to_version",
    "CARD_SORT_MANA_ASC",
    "CARD_SORT_DEFAULT",
    "CARD_SORT_MANA_DESC",
    "CARD_SORT_MANA_TYPE_ASC",
    "CARD_SORT_NAME_ASC",
    "CARD_SORT_TYPES_ASC",
    "CARD_SORT_UPDATED_DESC",
    "CARD_SORT_VALUES",
    "CardLifecycleFilter",
    "CardSort",
    "build_type_sort_lookup",
    "card_default_sort_key",
    "card_type_sort_key",
    "decode_field_sources",
    "decode_parsed_snapshot",
    "change_card_identity",
    "conflicting_card_id_for_key",
    "create_card_identity",
    "ensure_card_alias",
    "lock_card_identity_pools",
    "get_card",
    "get_card_image",
    "get_card_list_rows_by_version_ids",
    "get_latest_card_version",
    "get_latest_card_list_rows_by_card_ids",
    "list_card_generations",
    "list_cards_for_content_version",
    "list_cards",
    "list_cards_across_pools",
    "list_default_grouped_card_references",
    "list_matching_card_candidates",
    "list_matching_cards",
    "list_filtered_latest_card_version_reparse_sources",
    "list_latest_card_version_reparse_sources",
    "list_latest_active_card_image_sources",
    "promote_card_version",
    "resolve_image_file_path",
    "select_usable_card_image",
    "resolve_card_by_name_key",
    "save_parsed_card",
    "save_parsed_card_result",
    "set_card_mana_families",
    "update_latest_card_version",
]
