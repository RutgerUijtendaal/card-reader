from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from card_reader_core.models import Card

from .types import MAX_DECK_COPIES

DeckBoard = Literal["mainboard", "sideboard"]

MAINBOARD_COPY_LIMIT_RULE_ID = "mainboard_copy_limit"
LEGENDARY_COPY_LIMIT_RULE_ID = "legendary_copy_limit"
LEGENDARY_TYPE_KEY = "legendary"
LEGENDARY_COPY_LIMIT = 1


@dataclass(frozen=True)
class DeckConstraintEntry:
    card: Card
    quantity: int
    board: DeckBoard


@dataclass(frozen=True)
class DeckConstraintViolation:
    rule_id: str
    card_id: str
    message: str


class DeckConstraintEvaluator:
    def validate_entries(self, entries: list[DeckConstraintEntry]) -> list[DeckConstraintViolation]:
        return [
            *self._validate_mainboard_copy_limits(entries),
            *self._validate_legendary_copy_limits(entries),
        ]

    def _validate_mainboard_copy_limits(
        self,
        entries: list[DeckConstraintEntry],
    ) -> list[DeckConstraintViolation]:
        violations: list[DeckConstraintViolation] = []
        for entry in entries:
            if entry.board != "mainboard":
                continue
            if entry.quantity < 1 or entry.quantity > MAX_DECK_COPIES:
                violations.append(
                    DeckConstraintViolation(
                        rule_id=MAINBOARD_COPY_LIMIT_RULE_ID,
                        card_id=entry.card.id,
                        message=f"Each mainboard card quantity must be between 1 and {MAX_DECK_COPIES}.",
                    )
                )
        return violations

    def _validate_legendary_copy_limits(
        self,
        entries: list[DeckConstraintEntry],
    ) -> list[DeckConstraintViolation]:
        totals_by_card_id: dict[str, int] = {}
        legendary_cards: dict[str, Card] = {}
        for entry in entries:
            card_id = entry.card.id
            totals_by_card_id[card_id] = totals_by_card_id.get(card_id, 0) + entry.quantity
            if _card_has_type(entry.card, LEGENDARY_TYPE_KEY):
                legendary_cards[card_id] = entry.card

        return [
            DeckConstraintViolation(
                rule_id=LEGENDARY_COPY_LIMIT_RULE_ID,
                card_id=card_id,
                message=f"Legendary cards are limited to {LEGENDARY_COPY_LIMIT} copy per deck.",
            )
            for card_id in sorted(legendary_cards)
            if totals_by_card_id.get(card_id, 0) > LEGENDARY_COPY_LIMIT
        ]


def _card_has_type(card: Card, type_key: str) -> bool:
    version = card.latest_version
    if version is None:
        return False
    normalized_key = type_key.strip().lower()
    return any(row.type.key.strip().lower() == normalized_key for row in version.card_version_types.all())
