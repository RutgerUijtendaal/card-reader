from __future__ import annotations

from collections.abc import Iterable

from django.db.models import QuerySet

from card_reader_core.models import CardClassificationRule, CardPool


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
