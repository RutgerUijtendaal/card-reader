from __future__ import annotations

from typing import cast

from card_reader_core.models import Card, CardAlias, CardPool, CardVersion
from card_reader_core.repositories.cards import conflicting_card_id_for_key
from card_reader_core.repositories.helpers import normalize_slug_key

from .types import CardMergeAliasPreview


def build_alias_previews(*, target: Card, sources: list[Card]) -> list[CardMergeAliasPreview]:
    candidates: dict[str, str] = {}
    source_ids = [source.id for source in sources]
    for source in sources:
        if source.key:
            candidates[source.key] = source.label or source.key
    for alias in CardAlias.objects.filter(card_id__in=source_ids).order_by("key"):
        candidates[alias.key] = alias.label or alias.key
    for version in CardVersion.objects.filter(card_id__in=source_ids).order_by("created_at", "version_number", "id"):
        key = normalize_slug_key(version.name)
        if key:
            candidates.setdefault(key, version.name)

    aliases: list[CardMergeAliasPreview] = []
    for key, label in sorted(candidates.items()):
        if key == target.key:
            continue
        conflict_card_id = conflicting_card_id_for_key(
            key=key,
            card_pool=cast(CardPool, target.card_pool),
            excluded_card_ids={target.id, *source_ids},
        )
        aliases.append(CardMergeAliasPreview(key=key, label=label, conflict_card_id=conflict_card_id))
    return aliases
