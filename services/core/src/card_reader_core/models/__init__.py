from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

# Import model modules eagerly so Django registers every model class when the
# app loads. The lazy export mechanism below is fine for attribute access, but
# not sufficient for ORM relation resolution across modules.
_REGISTERED_MODEL_MODULES = (
    import_module(".card", __name__),
    import_module(".card_group", __name__),
    import_module(".card_version", __name__),
    import_module(".deck", __name__),
    import_module(".import_job", __name__),
    import_module(".metadata", __name__),
    import_module(".template", __name__),
)

if TYPE_CHECKING:
    from .base import now_utc
    from .card import (
        ACTIVE_CARD_LIFECYCLE_STATUS,
        ALL_CARD_LIFECYCLE_FILTER,
        CARD_LIFECYCLE_FILTER_VALUES,
        CARD_LIFECYCLE_STATUSES,
        DEFAULT_CARD_LIFECYCLE_FILTER,
        DEPRECATED_CARD_LIFECYCLE_STATUS,
        Card,
        CardAlias,
        CardLifecycleCarrier,
        CardLifecycleFilter,
        CardLifecycleStatus,
        CardMergeRedirect,
        active_card_lifecycle_q,
        card_is_deprecated,
        card_is_visible_for_lifecycle,
        card_lifecycle_filter_q,
        filter_queryset_by_card_lifecycle,
        is_card_lifecycle_status,
        normalize_card_lifecycle_filter,
    )
    from .card_group import CardGroup, CardGroupMember
    from .card_version import CardVersion, CardVersionImage, ParseResult
    from .deck import Deck, DeckEntry, DeckSideboard, DeckSideboardEntry, DeckVisibility
    from .import_job import ImportJob, ImportJobItem, ImportJobStatus
    from .metadata import (
        CardVersionMetadataSuggestion,
        CardVersionKeyword,
        CardVersionSymbol,
        CardVersionTag,
        CardVersionType,
        Keyword,
        MetadataSuggestion,
        Symbol,
        Tag,
        Type,
    )
    from .template import Template

_EXPORTS = {
    "now_utc": ".base",
    "ImportJobStatus": ".import_job",
    "ImportJob": ".import_job",
    "ImportJobItem": ".import_job",
    "Card": ".card",
    "CardAlias": ".card",
    "ACTIVE_CARD_LIFECYCLE_STATUS": ".card",
    "ALL_CARD_LIFECYCLE_FILTER": ".card",
    "CARD_LIFECYCLE_FILTER_VALUES": ".card",
    "CARD_LIFECYCLE_STATUSES": ".card",
    "DEFAULT_CARD_LIFECYCLE_FILTER": ".card",
    "DEPRECATED_CARD_LIFECYCLE_STATUS": ".card",
    "CardLifecycleFilter": ".card",
    "CardLifecycleCarrier": ".card",
    "CardLifecycleStatus": ".card",
    "CardMergeRedirect": ".card",
    "active_card_lifecycle_q": ".card",
    "card_is_deprecated": ".card",
    "card_is_visible_for_lifecycle": ".card",
    "card_lifecycle_filter_q": ".card",
    "filter_queryset_by_card_lifecycle": ".card",
    "is_card_lifecycle_status": ".card",
    "normalize_card_lifecycle_filter": ".card",
    "CardGroup": ".card_group",
    "CardGroupMember": ".card_group",
    "CardVersion": ".card_version",
    "CardVersionImage": ".card_version",
    "ParseResult": ".card_version",
    "Deck": ".deck",
    "DeckVisibility": ".deck",
    "DeckEntry": ".deck",
    "DeckSideboard": ".deck",
    "DeckSideboardEntry": ".deck",
    "Tag": ".metadata",
    "Symbol": ".metadata",
    "Keyword": ".metadata",
    "Type": ".metadata",
    "MetadataSuggestion": ".metadata",
    "CardVersionTag": ".metadata",
    "CardVersionSymbol": ".metadata",
    "CardVersionKeyword": ".metadata",
    "CardVersionType": ".metadata",
    "CardVersionMetadataSuggestion": ".metadata",
    "Template": ".template",
}

__all__ = [
    "now_utc",
    "ImportJobStatus",
    "ImportJob",
    "ImportJobItem",
    "Card",
    "CardAlias",
    "ACTIVE_CARD_LIFECYCLE_STATUS",
    "ALL_CARD_LIFECYCLE_FILTER",
    "CARD_LIFECYCLE_FILTER_VALUES",
    "CARD_LIFECYCLE_STATUSES",
    "DEFAULT_CARD_LIFECYCLE_FILTER",
    "DEPRECATED_CARD_LIFECYCLE_STATUS",
    "CardLifecycleFilter",
    "CardLifecycleCarrier",
    "CardLifecycleStatus",
    "CardMergeRedirect",
    "active_card_lifecycle_q",
    "card_is_deprecated",
    "card_is_visible_for_lifecycle",
    "card_lifecycle_filter_q",
    "filter_queryset_by_card_lifecycle",
    "is_card_lifecycle_status",
    "normalize_card_lifecycle_filter",
    "CardGroup",
    "CardGroupMember",
    "CardVersion",
    "CardVersionImage",
    "ParseResult",
    "Deck",
    "DeckVisibility",
    "DeckEntry",
    "DeckSideboard",
    "DeckSideboardEntry",
    "Tag",
    "Symbol",
    "Keyword",
    "Type",
    "MetadataSuggestion",
    "CardVersionTag",
    "CardVersionSymbol",
    "CardVersionKeyword",
    "CardVersionType",
    "CardVersionMetadataSuggestion",
    "Template",
]


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
