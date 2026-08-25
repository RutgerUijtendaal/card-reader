from __future__ import annotations

from card_reader_core.models import (
    HERO_CARD_ROLE,
    PLAYER_CARD_POOL,
    Deck,
    DeckEntry,
    card_has_role,
    card_is_deprecated,
)

from .constraints import DeckConstraintEntry, DeckConstraintEvaluator
from .types import DeckTotals, DeckValidationSummary


class DeckValidationService:
    def get_deck_validation(self, deck: Deck) -> DeckValidationSummary:
        entries = list(deck.entries.all())
        issues: list[str] = []
        warnings: list[str] = []
        deprecated_card_ids: set[str] = set()
        self._validate_hero(deck, issues=issues, deprecated_card_ids=deprecated_card_ids)
        total_cards, constraint_entries = self._validate_mainboard_entries(
            deck,
            entries=entries,
            issues=issues,
            deprecated_card_ids=deprecated_card_ids,
        )
        constraint_entries.extend(
            self._validate_sideboard_entries(
                deck,
                issues=issues,
                deprecated_card_ids=deprecated_card_ids,
            )
        )

        evaluation = DeckConstraintEvaluator().evaluate(hero_card=deck.hero_card, entries=constraint_entries)
        self._append_unique_violation_messages(
            issues,
            messages=[violation.message for violation in evaluation.hard_violations],
        )
        self._append_unique_violation_messages(
            warnings,
            messages=[violation.message for violation in evaluation.soft_violations],
        )

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

    def _validate_hero(
        self,
        deck: Deck,
        *,
        issues: list[str],
        deprecated_card_ids: set[str],
    ) -> None:
        if not card_has_role(deck.hero_card, HERO_CARD_ROLE):
            issues.append("Hero card must be marked as a hero.")
        if deck.hero_card.card_pool != PLAYER_CARD_POOL:
            issues.append("Hero card must belong to the Player pool.")
        if card_is_deprecated(deck.hero_card):
            issues.append("Hero card is deprecated.")
            deprecated_card_ids.add(deck.hero_card.id)

    def _validate_mainboard_entries(
        self,
        deck: Deck,
        *,
        entries: list[DeckEntry],
        issues: list[str],
        deprecated_card_ids: set[str],
    ) -> tuple[int, list[DeckConstraintEntry]]:
        total_cards = 0
        constraint_entries: list[DeckConstraintEntry] = []
        for entry in entries:
            quantity = int(entry.quantity)
            total_cards += quantity
            if card_is_deprecated(entry.card):
                deprecated_card_ids.add(entry.card.id)
            constraint_entries.append(
                DeckConstraintEntry(
                    card=entry.card,
                    quantity=quantity,
                    board="mainboard",
                )
            )
            if entry.card.card_pool != PLAYER_CARD_POOL:
                issues.append("Mainboard cards must belong to the Player pool.")
            if card_has_role(entry.card, HERO_CARD_ROLE):
                issues.append("Hero cards cannot appear in mainboard entries.")
                break
            if entry.card.id == deck.hero_card.id:
                issues.append("Hero card cannot also appear in the mainboard.")
                break
        return total_cards, constraint_entries

    def _validate_sideboard_entries(
        self,
        deck: Deck,
        *,
        issues: list[str],
        deprecated_card_ids: set[str],
    ) -> list[DeckConstraintEntry]:
        constraint_entries: list[DeckConstraintEntry] = []
        for sideboard in deck.sideboards.all():
            for entry in sideboard.entries.all():
                if entry.card.card_pool != PLAYER_CARD_POOL:
                    issues.append("Sideboard cards must belong to the Player pool.")
                if card_is_deprecated(entry.card):
                    deprecated_card_ids.add(entry.card.id)
                constraint_entries.append(
                    DeckConstraintEntry(
                        card=entry.card,
                        quantity=int(entry.quantity),
                        board="sideboard",
                    )
                )
        return constraint_entries

    def _append_unique_violation_messages(
        self,
        target: list[str],
        *,
        messages: list[str],
    ) -> None:
        for message in messages:
            if message not in target:
                target.append(message)

    def get_deck_totals(self, deck: Deck) -> DeckTotals:
        mainboard_entries = list(deck.entries.all())
        sideboards = list(deck.sideboards.all())
        mainboard_total_cards = sum(int(entry.quantity) for entry in mainboard_entries)
        overall_total_cards = mainboard_total_cards
        unique_card_ids = {str(entry.card.id) for entry in mainboard_entries}
        for sideboard in sideboards:
            for entry in sideboard.entries.all():
                overall_total_cards += int(entry.quantity)
                unique_card_ids.add(str(entry.card.id))
        return DeckTotals(
            overall_total_cards=overall_total_cards,
            overall_unique_cards=len(unique_card_ids),
            mainboard_total_cards=mainboard_total_cards,
            mainboard_unique_cards=len(mainboard_entries),
        )
