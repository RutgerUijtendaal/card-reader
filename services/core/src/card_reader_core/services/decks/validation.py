from __future__ import annotations

from card_reader_core.models import Deck, card_is_deprecated

from .constraints import DeckConstraintEntry, DeckConstraintEvaluator
from .types import DeckTotals, DeckValidationSummary


class DeckValidationService:
    def get_deck_validation(self, deck: Deck) -> DeckValidationSummary:
        entries = list(deck.entries.all())
        issues: list[str] = []
        warnings: list[str] = []
        total_cards = 0
        deprecated_card_ids: set[str] = set()
        constraint_entries: list[DeckConstraintEntry] = []

        if not deck.hero_card.is_hero:
            issues.append("Hero card must be marked as a hero.")
        if card_is_deprecated(deck.hero_card):
            issues.append("Hero card is deprecated.")
            deprecated_card_ids.add(deck.hero_card.id)

        for entry in entries:
            quantity = int(entry.quantity)
            total_cards += quantity
            if card_is_deprecated(entry.card):
                deprecated_card_ids.add(entry.card.id)
            constraint_entries.append(DeckConstraintEntry(card=entry.card, quantity=quantity, board="mainboard"))
            if entry.card.is_hero:
                issues.append("Hero cards cannot appear in mainboard entries.")
                break
            if entry.card.id == deck.hero_card.id:
                issues.append("Hero card cannot also appear in the mainboard.")
                break

        for sideboard in deck.sideboards.all():
            for sideboard_entry in sideboard.entries.all():
                if card_is_deprecated(sideboard_entry.card):
                    deprecated_card_ids.add(sideboard_entry.card.id)
                constraint_entries.append(
                    DeckConstraintEntry(
                        card=sideboard_entry.card,
                        quantity=int(sideboard_entry.quantity),
                        board="sideboard",
                    )
                )

        evaluation = DeckConstraintEvaluator().evaluate(hero_card=deck.hero_card, entries=constraint_entries)
        for violation in evaluation.hard_violations:
            if violation.message not in issues:
                issues.append(violation.message)
        for violation in evaluation.soft_violations:
            if violation.message not in warnings:
                warnings.append(violation.message)

        if deprecated_card_ids:
            issues.append("Deck contains deprecated cards.")

        is_valid = len(issues) == 0
        return DeckValidationSummary(
            is_valid=is_valid,
            status_label="Ready" if is_valid else "In Progress",
            total_cards=total_cards,
            unique_cards=len(entries),
            issues=issues,
            warnings=warnings,
            deprecated_card_count=len(deprecated_card_ids),
            deprecated_card_ids=sorted(deprecated_card_ids),
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
