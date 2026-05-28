from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from card_reader_core.models import (
    Card,
    CardAlias,
    CardGroup,
    CardGroupMember,
    CardMergeRedirect,
    CardVersion,
    Deck,
    DeckEntry,
    DeckSideboardEntry,
    now_utc,
)
from card_reader_core.repositories.helpers import normalize_slug_key


class CardMergeError(ValueError):
    pass


@dataclass(frozen=True)
class CardMergeCardSummary:
    id: str
    key: str
    label: str
    latest_name: str
    version_count: int


@dataclass(frozen=True)
class CardMergeAliasPreview:
    key: str
    label: str
    conflict_card_id: str | None


@dataclass(frozen=True)
class CardMergeRelationPreview:
    deck_entry_collisions: int
    sideboard_entry_collisions: int
    group_member_collisions: int
    hero_references: int
    anchored_groups: int


@dataclass(frozen=True)
class CardMergePreview:
    target: CardMergeCardSummary
    sources: list[CardMergeCardSummary]
    aliases: list[CardMergeAliasPreview]
    relations: CardMergeRelationPreview
    resulting_version_count: int
    blocking_conflicts: list[str]


def resolve_card_by_name_key(name: str) -> Card | None:
    key = normalize_slug_key(name)
    if not key:
        return None
    card = Card.objects.filter(key=key).first()
    if card is not None:
        return card
    alias = CardAlias.objects.select_related("card").filter(key=key).first()
    return alias.card if alias is not None else None


def ensure_card_alias(*, card: Card, key: str, label: str, allowed_conflict_card_ids: set[str] | None = None) -> CardAlias | None:
    normalized_key = normalize_slug_key(key)
    if not normalized_key or normalized_key == card.key:
        return None
    allowed_conflicts = allowed_conflict_card_ids or set()
    existing_card = Card.objects.filter(key=normalized_key).exclude(id=card.id).first()
    if existing_card is not None and existing_card.id not in allowed_conflicts:
        raise CardMergeError(f"Alias key '{normalized_key}' is already used by card '{existing_card.id}'.")
    existing_alias = CardAlias.objects.filter(key=normalized_key).first()
    if existing_alias is not None:
        existing_alias_card_id = str(getattr(existing_alias, "card_id"))
        if existing_alias_card_id != card.id:
            raise CardMergeError(f"Alias key '{normalized_key}' already points to card '{existing_alias_card_id}'.")
        return existing_alias
    return CardAlias.objects.create(card=card, key=normalized_key, label=label)


def preview_card_merge(*, target_card_id: str, source_card_ids: list[str]) -> CardMergePreview:
    target, sources = _load_merge_cards(target_card_id=target_card_id, source_card_ids=source_card_ids)
    aliases = _build_alias_previews(target=target, sources=sources)
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
        relations=CardMergeRelationPreview(
            deck_entry_collisions=_count_deck_entry_collisions(target.id, source_ids),
            sideboard_entry_collisions=_count_sideboard_entry_collisions(target.id, source_ids),
            group_member_collisions=_count_group_member_collisions(target.id, source_ids),
            hero_references=Deck.objects.filter(hero_card_id__in=source_ids).count(),
            anchored_groups=CardGroup.objects.filter(anchor_card_id__in=source_ids).count(),
        ),
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
    _merge_deck_references(target.id, source_ids)
    _merge_card_group_references(target.id, source_ids)
    _merge_card_versions(target.id, source_ids)
    CardAlias.objects.filter(card_id__in=source_ids).update(card=target, updated_at=now_utc())

    for alias in preview.aliases:
        ensure_card_alias(card=target, key=alias.key, label=alias.label, allowed_conflict_card_ids=set(source_ids))

    for source in sources:
        CardMergeRedirect.objects.update_or_create(
            old_card_id=source.id,
            defaults={"target_card": target},
        )
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


def _build_alias_previews(*, target: Card, sources: list[Card]) -> list[CardMergeAliasPreview]:
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
        existing_alias = CardAlias.objects.filter(key=key).first()
        existing_alias_card_id = str(getattr(existing_alias, "card_id")) if existing_alias is not None else None
        conflict_card_id = existing_alias_card_id if existing_alias_card_id is not None and existing_alias_card_id != target.id else None
        card_conflict = Card.objects.filter(key=key).exclude(id__in=[target.id, *source_ids]).first()
        if card_conflict is not None:
            conflict_card_id = card_conflict.id
        aliases.append(CardMergeAliasPreview(key=key, label=label, conflict_card_id=conflict_card_id))
    return aliases


def _count_deck_entry_collisions(target_id: str, source_ids: list[str]) -> int:
    collision_count = 0
    for deck_id in DeckEntry.objects.filter(card_id__in=source_ids).values_list("deck_id", flat=True):
        if DeckEntry.objects.filter(deck_id=deck_id, card_id=target_id).exists():
            collision_count += 1
    return collision_count


def _count_sideboard_entry_collisions(target_id: str, source_ids: list[str]) -> int:
    collision_count = 0
    for sideboard_id in DeckSideboardEntry.objects.filter(card_id__in=source_ids).values_list("sideboard_id", flat=True):
        if DeckSideboardEntry.objects.filter(sideboard_id=sideboard_id, card_id=target_id).exists():
            collision_count += 1
    return collision_count


def _count_group_member_collisions(target_id: str, source_ids: list[str]) -> int:
    collision_count = 0
    for group_id in CardGroupMember.objects.filter(card_id__in=source_ids).values_list("group_id", flat=True):
        if CardGroupMember.objects.filter(group_id=group_id, card_id=target_id).exists():
            collision_count += 1
    return collision_count


def _merge_deck_references(target_id: str, source_ids: list[str]) -> None:
    Deck.objects.filter(hero_card_id__in=source_ids).update(hero_card_id=target_id, updated_at=now_utc())

    for entry in list(DeckEntry.objects.filter(card_id__in=source_ids).select_for_update()):
        deck_id = str(getattr(entry, "deck_id"))
        existing = DeckEntry.objects.filter(deck_id=deck_id, card_id=target_id).first()
        if existing is None:
            setattr(entry, "card_id", target_id)
            entry.updated_at = now_utc()
            entry.save(update_fields=["card", "updated_at"])
            continue
        existing.quantity += entry.quantity
        existing.updated_at = now_utc()
        existing.save(update_fields=["quantity", "updated_at"])
        entry.delete()

    for sideboard_entry in list(DeckSideboardEntry.objects.filter(card_id__in=source_ids).select_for_update()):
        sideboard_id = str(getattr(sideboard_entry, "sideboard_id"))
        existing_sideboard_entry = DeckSideboardEntry.objects.filter(sideboard_id=sideboard_id, card_id=target_id).first()
        if existing_sideboard_entry is None:
            setattr(sideboard_entry, "card_id", target_id)
            sideboard_entry.updated_at = now_utc()
            sideboard_entry.save(update_fields=["card", "updated_at"])
            continue
        existing_sideboard_entry.quantity += sideboard_entry.quantity
        existing_sideboard_entry.updated_at = now_utc()
        existing_sideboard_entry.save(update_fields=["quantity", "updated_at"])
        sideboard_entry.delete()


def _merge_card_group_references(target_id: str, source_ids: list[str]) -> None:
    CardGroup.objects.filter(anchor_card_id__in=source_ids).update(anchor_card_id=target_id, updated_at=now_utc())
    affected_group_ids: set[str] = set()
    for member in list(CardGroupMember.objects.filter(card_id__in=source_ids).select_for_update()):
        group_id = str(getattr(member, "group_id"))
        affected_group_ids.add(group_id)
        existing = CardGroupMember.objects.filter(group_id=group_id, card_id=target_id).first()
        if existing is None:
            setattr(member, "card_id", target_id)
            member.updated_at = now_utc()
            member.save(update_fields=["card", "updated_at"])
            continue
        member.delete()

    for group_id in affected_group_ids:
        members = list(CardGroupMember.objects.filter(group_id=group_id).order_by("position", "created_at", "id"))
        for index, member in enumerate(members, start=1):
            if member.position != index:
                member.position = index
                member.updated_at = now_utc()
                member.save(update_fields=["position", "updated_at"])


def _merge_card_versions(target_id: str, source_ids: list[str]) -> None:
    target = Card.objects.select_related("latest_version").get(id=target_id)
    target_latest_id = target.latest_version.id if target.latest_version is not None else None
    source_versions = list(CardVersion.objects.filter(card_id__in=source_ids).select_for_update())
    temp_start = 1_000_000
    for offset, version in enumerate(source_versions):
        setattr(version, "card_id", target_id)
        version.version_number = temp_start + offset
        version.is_latest = False
        version.updated_at = now_utc()
        version.save(update_fields=["card", "version_number", "is_latest", "updated_at"])

    versions = list(CardVersion.objects.filter(card_id=target_id).select_related("card").order_by("created_at", "version_number", "id"))
    for offset, version in enumerate(versions, start=1):
        version.version_number = temp_start + 10_000 + offset
        version.updated_at = now_utc()
        version.save(update_fields=["version_number", "updated_at"])

    target_latest = next((version for version in versions if version.id == target_latest_id), None)
    ordered_versions = [version for version in versions if version.id != target_latest_id]
    if target_latest is not None:
        ordered_versions.append(target_latest)
    latest_version = ordered_versions[-1] if ordered_versions else None
    previous_id: str | None = None
    for index, version in enumerate(ordered_versions, start=1):
        version.version_number = index
        setattr(version, "previous_version_id", previous_id)
        version.is_latest = latest_version is not None and version.id == latest_version.id
        version.updated_at = now_utc()
        version.save(update_fields=["version_number", "previous_version", "is_latest", "updated_at"])
        previous_id = version.id

    target.latest_version = latest_version
    target.updated_at = now_utc()
    if latest_version is not None:
        target.label = latest_version.name or target.label
    target.save(update_fields=["latest_version", "label", "updated_at"])
