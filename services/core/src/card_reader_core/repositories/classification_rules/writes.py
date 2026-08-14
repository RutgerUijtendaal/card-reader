from __future__ import annotations

from card_reader_core.models import CardClassificationRule, Tag, Type, now_utc


def create_classification_rule(
    *,
    card_pool: str,
    target_kind: str,
    target_key: str,
    source_kind: str,
    tag: Tag | None,
    type: Type | None,
    enabled: bool,
) -> CardClassificationRule:
    return CardClassificationRule.objects.create(
        card_pool=card_pool,
        target_kind=target_kind,
        target_key=target_key,
        source_kind=source_kind,
        tag=tag,
        type=type,
        enabled=enabled,
    )


def update_classification_rule(
    rule: CardClassificationRule,
    *,
    updates: dict[str, object],
) -> CardClassificationRule:
    for field_name, value in updates.items():
        setattr(rule, field_name, value)
    rule.updated_at = now_utc()
    rule.save(update_fields=[*updates, "updated_at"])
    return rule


def delete_classification_rule(rule: CardClassificationRule) -> None:
    rule.delete()
