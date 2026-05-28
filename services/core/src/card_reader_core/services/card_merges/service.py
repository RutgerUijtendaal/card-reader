from __future__ import annotations

from django.db import transaction

from card_reader_core.models import Card, CardAlias, CardMergeRedirect, CardVersion, now_utc

from .aliases import build_alias_previews, ensure_card_alias
from .relations import merge_card_group_references, merge_deck_references, preview_relation_changes
from .types import CardMergeCardSummary, CardMergeError, CardMergePreview
from .versions import merge_card_versions


def preview_card_merge(*, target_card_id: str, source_card_ids: list[str]) -> CardMergePreview:
    target, sources = _load_merge_cards(target_card_id=target_card_id, source_card_ids=source_card_ids)
    aliases = build_alias_previews(target=target, sources=sources)
    blocking_conflicts = [
        f"Alias key '{alias.key}' already points to card '{alias.conflict_card_id}'."
        for alias in aliases
        if alias.conflict_card_id is not None and alias.conflict_card_id not in {source.id for source in sources}
    ]
    source_ids = [source.id for source in sources]
    return CardMergePreview(
        target=_card_summary(target),
        sources=[_card_summary(source) for source in sources],
        aliases=aliases,
        relations=preview_relation_changes(target_id=target.id, source_ids=source_ids),
        resulting_version_count=CardVersion.objects.filter(card_id__in=[target.id, *source_ids]).count(),
        blocking_conflicts=blocking_conflicts,
    )


@transaction.atomic
def merge_cards(*, target_card_id: str, source_card_ids: list[str]) -> CardMergePreview:
    target, sources = _load_merge_cards(
        target_card_id=target_card_id,
        source_card_ids=source_card_ids,
        for_update=True,
    )
    preview = preview_card_merge(target_card_id=target.id, source_card_ids=[source.id for source in sources])
    if preview.blocking_conflicts:
        raise CardMergeError("Merge has blocking alias conflicts.")

    source_ids = [source.id for source in sources]
    merge_deck_references(target.id, source_ids)
    merge_card_group_references(target.id, source_ids)
    merge_card_versions(target.id, source_ids)
    CardAlias.objects.filter(card_id__in=source_ids).update(card=target, updated_at=now_utc())

    for alias in preview.aliases:
        ensure_card_alias(card=target, key=alias.key, label=alias.label, allowed_conflict_card_ids=set(source_ids))

    for source in sources:
        CardMergeRedirect.objects.update_or_create(
            old_card_id=source.id,
            defaults={"target_card": target},
        )
    CardMergeRedirect.objects.filter(target_card_id__in=source_ids).update(target_card=target, updated_at=now_utc())
    Card.objects.filter(id__in=source_ids).delete()
    target.updated_at = now_utc()
    if target.latest_version is not None:
        target.label = target.latest_version.name or target.label
    target.save(update_fields=["label", "updated_at"])
    return preview_card_merge(target_card_id=target.id, source_card_ids=[])


def _load_merge_cards(
    *,
    target_card_id: str,
    source_card_ids: list[str],
    for_update: bool = False,
) -> tuple[Card, list[Card]]:
    normalized_source_ids = [card_id for card_id in dict.fromkeys(source_card_ids) if card_id]
    if not target_card_id:
        raise CardMergeError("Target card is required.")
    if target_card_id in normalized_source_ids:
        raise CardMergeError("Target card cannot also be a source card.")
    queryset = Card.objects.select_related("latest_version")
    if for_update:
        queryset = queryset.select_for_update()
    cards = {card.id: card for card in queryset.filter(id__in=[target_card_id, *normalized_source_ids])}
    target = cards.get(target_card_id)
    if target is None:
        raise CardMergeError("Target card not found.")
    missing = [card_id for card_id in normalized_source_ids if card_id not in cards]
    if missing:
        raise CardMergeError("One or more source cards were not found.")
    return target, [cards[card_id] for card_id in normalized_source_ids]


def _card_summary(card: Card) -> CardMergeCardSummary:
    latest = card.latest_version
    return CardMergeCardSummary(
        id=card.id,
        key=card.key,
        label=card.label,
        latest_name=latest.name if latest is not None else "",
        version_count=CardVersion.objects.filter(card_id=card.id).count(),
    )
