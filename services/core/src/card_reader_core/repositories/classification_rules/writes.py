from __future__ import annotations

from card_reader_core.models import CardClassificationRule, Symbol, Tag, Type, now_utc


def create_classification_rule(
    *,
    card_pool: str,
    target_kind: str,
    target_key: str,
    source_kind: str,
    tag: Tag | None,
    type: Type | None,
    symbol: Symbol | None,
    enabled: bool,
) -> CardClassificationRule:
    return CardClassificationRule.objects.create(
        card_pool=card_pool,
        target_kind=target_kind,
        target_key=target_key,
        source_kind=source_kind,
        tag=tag,
        type=type,
        symbol=symbol,
        enabled=enabled,
    )


def update_classification_rule(
    rule: CardClassificationRule,
    *,
    updates: dict[str, object],
) -> CardClassificationRule | None:
    updated_at = now_utc()
    updated_count = CardClassificationRule.objects.filter(
        id=rule.id,
        updated_at=rule.updated_at,
    ).update(**updates, updated_at=updated_at)
    if updated_count == 0:
        return None
    return (
        CardClassificationRule.objects.select_related("tag", "type", "symbol")
        .filter(id=rule.id)
        .first()
    )


def delete_classification_rule(rule: CardClassificationRule) -> None:
    rule.delete()
