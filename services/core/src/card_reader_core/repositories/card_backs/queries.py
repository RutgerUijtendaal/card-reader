from __future__ import annotations

from card_reader_core.models import CardBack


def list_card_backs() -> list[CardBack]:
    return list(CardBack.objects.order_by("-created_at", "-id"))


def get_current_card_back() -> CardBack | None:
    return CardBack.objects.filter(is_current=True).order_by("-updated_at", "-created_at", "-id").first()


def get_card_back(card_back_id: str) -> CardBack | None:
    return CardBack.objects.filter(id=card_back_id).first()
