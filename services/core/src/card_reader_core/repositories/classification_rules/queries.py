from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Count, QuerySet

from card_reader_core.models import (
    ACTIVE_CARD_LIFECYCLE_STATUS,
    Card,
    CardClassificationRule,
    CardFactionAssignment,
    CardPool,
    CardRoleAssignment,
)


@dataclass(frozen=True)
class ClassificationUsageCounts:
    roles: dict[tuple[str, str], int]
    factions: dict[tuple[str, str], int]
    normal: dict[str, int]
    no_faction: dict[str, int]


def classification_rule_queryset() -> QuerySet[CardClassificationRule]:
    return CardClassificationRule.objects.select_related("tag", "type")


def get_classification_rule(rule_id: str) -> CardClassificationRule | None:
    return classification_rule_queryset().filter(id=rule_id).first()


def list_classification_rules(
    *,
    card_pool: CardPool | None = None,
    enabled: bool | None = None,
    target_kinds: Iterable[str] | None = None,
) -> list[CardClassificationRule]:
    query = classification_rule_queryset()
    if card_pool is not None:
        query = query.filter(card_pool=card_pool)
    if enabled is not None:
        query = query.filter(enabled=enabled)
    if target_kinds is not None:
        query = query.filter(target_kind__in=tuple(target_kinds))
    return list(
        query.order_by(
            "card_pool",
            "target_kind",
            "target_key",
            "source_kind",
            "tag__key",
            "type__key",
            "id",
        )
    )


def list_rules_for_source(*, source_kind: str, source_id: str) -> list[CardClassificationRule]:
    lookup = {f"{source_kind}_id": source_id}
    return list(
        classification_rule_queryset()
        .filter(source_kind=source_kind, **lookup)
        .order_by("card_pool", "target_kind", "target_key", "id")
    )


def get_classification_usage_counts(
    *, card_pools: Iterable[CardPool]
) -> ClassificationUsageCounts:
    allowed_pools = tuple(card_pools)
    role_usage = {
        (str(row["role"]), str(row["card__card_pool"])): int(row["count"])
        for row in (
            CardRoleAssignment.objects.filter(
                card__card_pool__in=allowed_pools,
                card__lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
            )
            .values("role", "card__card_pool")
            .annotate(count=Count("card_id"))
        )
    }
    faction_usage = {
        (str(row["faction"]), str(row["card__card_pool"])): int(row["count"])
        for row in (
            CardFactionAssignment.objects.filter(
                card__card_pool__in=allowed_pools,
                card__lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
            )
            .values("faction", "card__card_pool")
            .annotate(count=Count("card_id"))
        )
    }
    normal_usage: dict[str, int] = {
        pool: Card.objects.filter(
            card_pool=pool,
            lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
            role_assignments__isnull=True,
        ).count()
        for pool in allowed_pools
    }
    no_faction_usage: dict[str, int] = {
        pool: Card.objects.filter(
            card_pool=pool,
            lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
            faction_assignments__isnull=True,
        ).count()
        for pool in allowed_pools
    }
    return ClassificationUsageCounts(
        roles=role_usage,
        factions=faction_usage,
        normal=normal_usage,
        no_faction=no_faction_usage,
    )
