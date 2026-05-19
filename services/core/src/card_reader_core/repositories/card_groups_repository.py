from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch, QuerySet

from card_reader_core.models import Card, CardGroup, CardGroupMember


def card_group_key_exists(*, key: str, exclude_id: str | None = None) -> bool:
    queryset = CardGroup.objects.filter(key=key)
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    return queryset.exists()


def get_card_group(group_id: str) -> CardGroup | None:
    return _group_queryset().filter(id=group_id).first()


def list_card_groups() -> list[CardGroup]:
    return list(_group_queryset().order_by("name", "created_at"))


def list_card_groups_for_card(card_id: str) -> list[CardGroup]:
    return list(_group_queryset().filter(members__card_id=card_id).distinct().order_by("name", "created_at"))


def list_card_groups_for_cards(card_ids: list[str]) -> list[CardGroup]:
    if not card_ids:
        return []
    return list(_group_queryset().filter(members__card_id__in=card_ids).distinct())


def get_cards(card_ids: list[str]) -> dict[str, Card]:
    if not card_ids:
        return {}
    return {
        card.id: card
        for card in Card.objects.filter(id__in=card_ids).select_related(
            "latest_version",
            "latest_version__template",
            "latest_version__previous_version",
        )
    }


def create_card_group(*, key: str, name: str, anchor_card: Card) -> CardGroup:
    return CardGroup.objects.create(key=key, name=name, anchor_card=anchor_card)


def update_card_group(*, group_id: str, updates: dict[str, object]) -> CardGroup | None:
    row = CardGroup.objects.filter(id=group_id).first()
    if row is None:
        return None
    for field_name, value in updates.items():
        setattr(row, field_name, value)
    row.save(update_fields=[*updates.keys(), "updated_at"])
    return row


def delete_card_group(*, group_id: str) -> bool:
    deleted, _ = CardGroup.objects.filter(id=group_id).delete()
    return deleted > 0


@transaction.atomic
def replace_card_group_members(*, group: CardGroup, ordered_card_ids: list[str]) -> None:
    CardGroupMember.objects.filter(group=group).delete()
    CardGroupMember.objects.bulk_create(
        [
            CardGroupMember(group=group, card_id=card_id, position=index + 1)
            for index, card_id in enumerate(ordered_card_ids)
        ]
    )


def _group_queryset() -> QuerySet[CardGroup]:
    return CardGroup.objects.select_related(
        "anchor_card",
        "anchor_card__latest_version",
        "anchor_card__latest_version__template",
        "anchor_card__latest_version__previous_version",
    ).prefetch_related(
        Prefetch(
            "members",
            queryset=CardGroupMember.objects.select_related(
                "card",
                "card__latest_version",
                "card__latest_version__template",
                "card__latest_version__previous_version",
            ).order_by("position", "created_at"),
        )
    )
