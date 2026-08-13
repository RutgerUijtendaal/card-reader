from __future__ import annotations

from typing import cast

from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F

from card_reader_core.models import (
    CARD_POOLS,
    Card,
    CardAlias,
    CardFaction,
    CardFactionAssignment,
    CardIdentityPoolLock,
    CardPool,
    card_faction_identity_key,
    card_faction_keys,
    normalize_card_factions,
    now_utc,
)

from ..helpers import normalize_slug_key
from .types import CardIdentityConflict


def lock_card_identity_pools(*card_pools: CardPool) -> None:
    """Serialize primary/alias namespace writes for the requested pools."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("Card identity pool locks require an active database transaction.")
    requested = set(card_pools)
    try:
        for card_pool in CARD_POOLS:
            if card_pool not in requested:
                continue
            updated = CardIdentityPoolLock.objects.filter(card_pool=card_pool).update(
                revision=F("revision") + 1,
                updated_at=now_utc(),
            )
            if updated != 1:
                raise CardIdentityConflict(
                    f"Identity namespace lock is missing for the {card_pool} pool."
                )
    except OperationalError as exc:
        raise CardIdentityConflict(
            "The card identity namespace is being changed by another request; retry the operation."
        ) from exc


def resolve_card_by_name_key(
    *, name: str, card_pool: CardPool, card_factions: tuple[CardFaction, ...] = ()
) -> Card | None:
    key = normalize_slug_key(name)
    if not key:
        return None
    faction_key = card_faction_identity_key(card_factions)
    card = Card.objects.filter(
        card_pool=card_pool,
        faction_identity_key=faction_key,
        key=key,
    ).first()
    if card is not None:
        return card
    alias = (
        CardAlias.objects.select_related("card")
        .filter(card_pool=card_pool, faction_identity_key=faction_key, key=key)
        .first()
    )
    return alias.card if alias is not None else None


def conflicting_card_id_for_key(
    *,
    key: str,
    card_pool: CardPool,
    card_factions: tuple[CardFaction, ...] = (),
    excluded_card_ids: set[str] | None = None,
) -> str | None:
    normalized_key = normalize_slug_key(key)
    if not normalized_key:
        return None
    excluded = excluded_card_ids or set()
    faction_key = card_faction_identity_key(card_factions)
    card = (
        Card.objects.filter(
            card_pool=card_pool,
            faction_identity_key=faction_key,
            key=normalized_key,
        )
        .exclude(id__in=excluded)
        .first()
    )
    if card is not None:
        return card.id
    alias = (
        CardAlias.objects.filter(
            card_pool=card_pool,
            faction_identity_key=faction_key,
            key=normalized_key,
        )
        .exclude(card_id__in=excluded)
        .first()
    )
    return str(getattr(alias, "card_id")) if alias is not None else None


@transaction.atomic
def ensure_card_alias(
    *,
    card: Card,
    key: str,
    label: str,
    allowed_conflict_card_ids: set[str] | None = None,
) -> CardAlias | None:
    card_pool = cast(CardPool, card.card_pool)
    factions = card_faction_keys(card)
    lock_card_identity_pools(card_pool)
    normalized_key = normalize_slug_key(key)
    if not normalized_key or normalized_key == card.key:
        return None
    allowed_conflicts = allowed_conflict_card_ids or set()
    conflict_id = conflicting_card_id_for_key(
        key=normalized_key,
        card_pool=card_pool,
        card_factions=factions,
        excluded_card_ids={card.id, *allowed_conflicts},
    )
    if conflict_id is not None:
        raise CardIdentityConflict(
            f"Alias key '{normalized_key}' is already used by card '{conflict_id}' in the {card.card_pool} pool."
        )
    existing = CardAlias.objects.filter(
        card_id=card.id,
        card_pool=card.card_pool,
        faction_identity_key=card.faction_identity_key,
        key=normalized_key,
    ).first()
    if existing is not None:
        return existing
    try:
        with transaction.atomic():
            return CardAlias.objects.create(
                card=card,
                card_pool=card.card_pool,
                faction_identity_key=card.faction_identity_key,
                key=normalized_key,
                label=label,
            )
    except IntegrityError as exc:
        conflict_id = conflicting_card_id_for_key(
            key=normalized_key,
            card_pool=card_pool,
            card_factions=factions,
            excluded_card_ids={card.id, *allowed_conflicts},
        )
        if conflict_id is not None:
            raise CardIdentityConflict(
                f"Alias key '{normalized_key}' is already used by card '{conflict_id}' in the {card.card_pool} pool."
            ) from exc
        existing = CardAlias.objects.filter(
            card_id=card.id,
            card_pool=card.card_pool,
            faction_identity_key=card.faction_identity_key,
            key=normalized_key,
        ).first()
        if existing is not None:
            return existing
        raise


@transaction.atomic
def create_card_identity(
    *, name: str, card_pool: CardPool, card_factions: tuple[CardFaction, ...] = ()
) -> tuple[Card, bool]:
    lock_card_identity_pools(card_pool)
    normalized_factions = normalize_card_factions(card_factions)
    faction_key = card_faction_identity_key(normalized_factions)
    existing = resolve_card_by_name_key(
        name=name,
        card_pool=card_pool,
        card_factions=normalized_factions,
    )
    if existing is not None:
        return existing, False
    key = normalize_slug_key(name)
    if not key:
        raise CardIdentityConflict("Card name must produce a non-empty identity key.")
    alias_conflict = CardAlias.objects.filter(
        card_pool=card_pool,
        faction_identity_key=faction_key,
        key=key,
    ).first()
    if alias_conflict is not None:
        return alias_conflict.card, False
    try:
        with transaction.atomic():
            card = Card.objects.create(
                key=key,
                label=name,
                card_pool=card_pool,
                faction_identity_key=faction_key,
            )
            CardFactionAssignment.objects.bulk_create(
                [CardFactionAssignment(card=card, faction=faction) for faction in normalized_factions]
            )
            return card, True
    except IntegrityError as exc:
        winner = resolve_card_by_name_key(
            name=name,
            card_pool=card_pool,
            card_factions=normalized_factions,
        )
        if winner is not None:
            return winner, False
        raise CardIdentityConflict(
            f"Card key '{key}' conflicts with another identity in the {card_pool} pool."
        ) from exc


@transaction.atomic
def change_card_identity(
    *,
    card: Card,
    label: str | None = None,
    card_pool: CardPool | None = None,
    card_factions: tuple[CardFaction, ...] | None = None,
) -> Card:
    lock_card_identity_pools(*CARD_POOLS)
    locked = Card.objects.select_for_update().get(id=card.id)
    destination_pool = card_pool or cast(CardPool, locked.card_pool)
    destination_factions = (
        card_faction_keys(locked)
        if card_factions is None
        else normalize_card_factions(card_factions)
    )
    destination_faction_key = card_faction_identity_key(destination_factions)
    destination_label = locked.label if label is None else label
    destination_key = normalize_slug_key(destination_label)
    if not destination_key:
        raise CardIdentityConflict("Card name must produce a non-empty identity key.")

    aliases = list(CardAlias.objects.select_for_update().filter(card_id=locked.id))
    alias_labels = {alias.key: alias.label for alias in aliases if alias.key != destination_key}
    if destination_key != locked.key:
        alias_labels.setdefault(locked.key, locked.label)

    primary_conflict = conflicting_card_id_for_key(
        key=destination_key,
        card_pool=destination_pool,
        card_factions=destination_factions,
        excluded_card_ids={locked.id},
    )
    if primary_conflict is not None:
        raise CardIdentityConflict(
            f"Card name conflicts with card '{primary_conflict}' in the {destination_pool} pool."
        )
    for alias_key in alias_labels:
        alias_conflict = conflicting_card_id_for_key(
            key=alias_key,
            card_pool=destination_pool,
            card_factions=destination_factions,
            excluded_card_ids={locked.id},
        )
        if alias_conflict is not None:
            raise CardIdentityConflict(
                f"Alias key '{alias_key}' conflicts with card '{alias_conflict}' in the {destination_pool} pool."
            )

    try:
        with transaction.atomic():
            CardAlias.objects.filter(card_id=locked.id, key=destination_key).delete()
            CardAlias.objects.filter(card_id=locked.id).update(
                card_pool=destination_pool,
                faction_identity_key=destination_faction_key,
                updated_at=now_utc(),
            )
            locked.card_pool = destination_pool
            locked.faction_identity_key = destination_faction_key
            locked.label = destination_label
            locked.key = destination_key
            locked.updated_at = now_utc()
            locked.save(
                update_fields=[
                    "card_pool",
                    "faction_identity_key",
                    "label",
                    "key",
                    "updated_at",
                ]
            )
            CardFactionAssignment.objects.filter(card_id=locked.id).delete()
            CardFactionAssignment.objects.bulk_create(
                [CardFactionAssignment(card=locked, faction=faction) for faction in destination_factions]
            )
            locked_prefetches = getattr(locked, "_prefetched_objects_cache", None)
            if locked_prefetches is not None:
                locked_prefetches.pop("faction_assignments", None)

            existing_alias_keys = set(
                CardAlias.objects.filter(card_id=locked.id).values_list("key", flat=True)
            )
            CardAlias.objects.bulk_create(
                [
                    CardAlias(
                        card=locked,
                        card_pool=destination_pool,
                        faction_identity_key=destination_faction_key,
                        key=alias_key,
                        label=alias_label,
                    )
                    for alias_key, alias_label in alias_labels.items()
                    if alias_key not in existing_alias_keys
                ]
            )
    except IntegrityError as exc:
        conflict_id = conflicting_card_id_for_key(
            key=destination_key,
            card_pool=destination_pool,
            card_factions=destination_factions,
            excluded_card_ids={locked.id},
        )
        conflict_suffix = f" with card '{conflict_id}'" if conflict_id is not None else ""
        raise CardIdentityConflict(
            f"Card identity conflicts{conflict_suffix} in the {destination_pool} pool."
        ) from exc

    card.card_pool = locked.card_pool
    card.faction_identity_key = locked.faction_identity_key
    card.label = locked.label
    card.key = locked.key
    card.updated_at = locked.updated_at
    card_prefetches = getattr(card, "_prefetched_objects_cache", None)
    if card_prefetches is not None:
        card_prefetches.pop("faction_assignments", None)
    return card
