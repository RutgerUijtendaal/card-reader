from __future__ import annotations

from typing import cast

from django.db import IntegrityError, transaction

from card_reader_core.models import Card, CardAlias, CardPool, now_utc

from ..helpers import normalize_slug_key
from .types import CardIdentityConflict


def resolve_card_by_name_key(*, name: str, card_pool: CardPool) -> Card | None:
    key = normalize_slug_key(name)
    if not key:
        return None
    card = Card.objects.filter(card_pool=card_pool, key=key).first()
    if card is not None:
        return card
    alias = (
        CardAlias.objects.select_related("card")
        .filter(card_pool=card_pool, key=key)
        .first()
    )
    return alias.card if alias is not None else None


def conflicting_card_id_for_key(
    *,
    key: str,
    card_pool: CardPool,
    excluded_card_ids: set[str] | None = None,
) -> str | None:
    normalized_key = normalize_slug_key(key)
    if not normalized_key:
        return None
    excluded = excluded_card_ids or set()
    card = Card.objects.filter(card_pool=card_pool, key=normalized_key).exclude(id__in=excluded).first()
    if card is not None:
        return card.id
    alias = (
        CardAlias.objects.filter(card_pool=card_pool, key=normalized_key)
        .exclude(card_id__in=excluded)
        .first()
    )
    return str(getattr(alias, "card_id")) if alias is not None else None


def ensure_card_alias(
    *,
    card: Card,
    key: str,
    label: str,
    allowed_conflict_card_ids: set[str] | None = None,
) -> CardAlias | None:
    normalized_key = normalize_slug_key(key)
    if not normalized_key or normalized_key == card.key:
        return None
    allowed_conflicts = allowed_conflict_card_ids or set()
    conflict_id = conflicting_card_id_for_key(
        key=normalized_key,
        card_pool=cast(CardPool, card.card_pool),
        excluded_card_ids={card.id, *allowed_conflicts},
    )
    if conflict_id is not None:
        raise CardIdentityConflict(
            f"Alias key '{normalized_key}' is already used by card '{conflict_id}' in the {card.card_pool} pool."
        )
    existing = CardAlias.objects.filter(
        card_id=card.id,
        card_pool=card.card_pool,
        key=normalized_key,
    ).first()
    if existing is not None:
        return existing
    try:
        with transaction.atomic():
            return CardAlias.objects.create(
                card=card,
                card_pool=card.card_pool,
                key=normalized_key,
                label=label,
            )
    except IntegrityError as exc:
        conflict_id = conflicting_card_id_for_key(
            key=normalized_key,
            card_pool=cast(CardPool, card.card_pool),
            excluded_card_ids={card.id, *allowed_conflicts},
        )
        if conflict_id is not None:
            raise CardIdentityConflict(
                f"Alias key '{normalized_key}' is already used by card '{conflict_id}' in the {card.card_pool} pool."
            ) from exc
        existing = CardAlias.objects.filter(
            card_id=card.id,
            card_pool=card.card_pool,
            key=normalized_key,
        ).first()
        if existing is not None:
            return existing
        raise


def create_card_identity(*, name: str, card_pool: CardPool) -> tuple[Card, bool]:
    existing = resolve_card_by_name_key(name=name, card_pool=card_pool)
    if existing is not None:
        return existing, False
    key = normalize_slug_key(name)
    alias_conflict = CardAlias.objects.filter(card_pool=card_pool, key=key).first()
    if alias_conflict is not None:
        return alias_conflict.card, False
    try:
        with transaction.atomic():
            return Card.objects.create(key=key, label=name, card_pool=card_pool), True
    except IntegrityError as exc:
        winner = resolve_card_by_name_key(name=name, card_pool=card_pool)
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
) -> Card:
    locked = Card.objects.select_for_update().get(id=card.id)
    destination_pool = card_pool or cast(CardPool, locked.card_pool)
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
            excluded_card_ids={locked.id},
        )
        if alias_conflict is not None:
            raise CardIdentityConflict(
                f"Alias key '{alias_key}' conflicts with card '{alias_conflict}' in the {destination_pool} pool."
            )

    CardAlias.objects.filter(card_id=locked.id, key=destination_key).delete()
    CardAlias.objects.filter(card_id=locked.id).update(
        card_pool=destination_pool,
        updated_at=now_utc(),
    )
    locked.card_pool = destination_pool
    locked.label = destination_label
    locked.key = destination_key
    locked.updated_at = now_utc()
    locked.save(update_fields=["card_pool", "label", "key", "updated_at"])

    existing_alias_keys = set(
        CardAlias.objects.filter(card_id=locked.id).values_list("key", flat=True)
    )
    CardAlias.objects.bulk_create(
        [
            CardAlias(
                card=locked,
                card_pool=destination_pool,
                key=alias_key,
                label=alias_label,
            )
            for alias_key, alias_label in alias_labels.items()
            if alias_key not in existing_alias_keys
        ]
    )

    card.card_pool = locked.card_pool
    card.label = locked.label
    card.key = locked.key
    card.updated_at = locked.updated_at
    return card
