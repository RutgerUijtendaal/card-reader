from __future__ import annotations

from django.db.models import Count

from card_reader_core.models import (
    Card,
    CardBack,
    CardBackFactionDefault,
    CardBackPoolDefault,
    CardBackRoleDefault,
)


def list_card_backs() -> list[CardBack]:
    return list(
        CardBack.objects.annotate(override_card_count=Count("card_overrides", distinct=True))
        .prefetch_related("faction_defaults", "pool_defaults", "role_defaults")
        .order_by("-created_at", "-id")
    )


def get_pool_default_rows() -> list[CardBackPoolDefault]:
    return list(CardBackPoolDefault.objects.select_related("card_back").order_by("card_pool"))


def get_faction_default_rows() -> list[CardBackFactionDefault]:
    return list(CardBackFactionDefault.objects.select_related("card_back").order_by("faction"))


def get_role_default_rows() -> list[CardBackRoleDefault]:
    return list(CardBackRoleDefault.objects.select_related("card_back").order_by("role"))


def get_card_back(card_back_id: str) -> CardBack | None:
    return CardBack.objects.filter(id=card_back_id).first()


def get_cards_for_card_back_resolution(card_ids: list[str]) -> list[Card]:
    return list(
        Card.objects.filter(id__in=card_ids)
        .select_related("card_back_override")
        .prefetch_related("faction_assignments", "role_assignments")
        .only("id", "card_pool", "card_back_override_id", "card_back_override")
    )
