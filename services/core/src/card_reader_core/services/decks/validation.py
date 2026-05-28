from __future__ import annotations

from card_reader_core.models import Card, Deck

from .types import (
    MAX_DECK_COPIES,
    MAX_MAINBOARD_CARD_COUNT,
    MIN_MAINBOARD_CARD_COUNT,
    MIN_MAINBOARD_MANA_TYPE_COUNT,
    DeckTotals,
    DeckValidationSummary,
)


class DeckValidationService:
    def get_deck_validation(self, deck: Deck) -> DeckValidationSummary:
        entries = list(deck.entries.all())
        issues: list[str] = []
        total_cards = 0
        mana_type_cards = 0

        if not deck.hero_card.is_hero:
            issues.append("Hero card must be marked as a hero.")

        for entry in entries:
            quantity = int(entry.quantity)
            total_cards += quantity
            if quantity < 1 or quantity > MAX_DECK_COPIES:
                issues.append(f"Each mainboard card quantity must be between 1 and {MAX_DECK_COPIES}.")
                break
            if entry.card.is_hero:
                issues.append("Hero cards cannot appear in mainboard entries.")
                break
            if entry.card.id == deck.hero_card.id:
                issues.append("Hero card cannot also appear in the mainboard.")
                break
            if self._card_has_type(entry.card, "mana"):
                mana_type_cards += quantity

        if total_cards < MIN_MAINBOARD_CARD_COUNT:
            issues.append(f"Deck must contain at least {MIN_MAINBOARD_CARD_COUNT} mainboard cards.")
        if total_cards > MAX_MAINBOARD_CARD_COUNT:
            issues.append(f"Deck cannot contain more than {MAX_MAINBOARD_CARD_COUNT} mainboard cards.")
        if mana_type_cards < MIN_MAINBOARD_MANA_TYPE_COUNT:
            issues.append(f"Deck must contain at least {MIN_MAINBOARD_MANA_TYPE_COUNT} mainboard cards with type 'Mana'.")

        is_valid = len(issues) == 0
        return DeckValidationSummary(
            is_valid=is_valid,
            status_label="Ready" if is_valid else "In Progress",
            total_cards=total_cards,
            unique_cards=len(entries),
            issues=issues,
        )

    def get_deck_totals(self, deck: Deck) -> DeckTotals:
        mainboard_entries = list(deck.entries.all())
        sideboards = list(deck.sideboards.all())
        mainboard_total_cards = sum(int(entry.quantity) for entry in mainboard_entries)
        overall_total_cards = mainboard_total_cards + sum(
            int(entry.quantity)
            for sideboard in sideboards
            for entry in sideboard.entries.all()
        )
        unique_card_ids = {
            str(entry.card.id)
            for entry in mainboard_entries
        } | {
            str(entry.card.id)
            for sideboard in sideboards
            for entry in sideboard.entries.all()
        }
        return DeckTotals(
            overall_total_cards=overall_total_cards,
            overall_unique_cards=len(unique_card_ids),
            mainboard_total_cards=mainboard_total_cards,
            mainboard_unique_cards=len(mainboard_entries),
        )

    def _card_has_type(self, card: Card, type_key: str) -> bool:
        version = card.latest_version
        if version is None:
            return False
        normalized_key = type_key.strip().lower()
        return any(row.type.key.strip().lower() == normalized_key for row in version.card_version_types.all())
