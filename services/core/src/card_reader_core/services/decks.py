from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from django.db import transaction

from card_reader_core.models import Card, Deck
from card_reader_core.repositories import (
    create_deck,
    delete_deck,
    get_cards_by_ids,
    get_deck_for_viewer,
    get_owner_deck,
    get_public_deck,
    list_owner_decks,
    list_public_decks,
    replace_deck_entries,
    update_deck,
)
from card_reader_core.repositories.decks_repository import get_deck_card

MAX_DECK_COPIES = 4
MIN_MAINBOARD_CARD_COUNT = 40
MAX_MAINBOARD_CARD_COUNT = 60


@dataclass(frozen=True)
class DeckEntryInput:
    card_id: str
    quantity: int


@dataclass(frozen=True)
class DeckValidationSummary:
    is_valid: bool
    status_label: str
    total_cards: int
    unique_cards: int
    issues: list[str]


class DeckService:
    def list_public_decks(self) -> list[Deck]:
        return [deck for deck in cast(list[Deck], list_public_decks()) if self.get_deck_validation(deck).is_valid]

    def list_owner_decks(self, owner_id: str) -> list[Deck]:
        return cast(list[Deck], list_owner_decks(owner_id))

    def get_public_deck(self, deck_id: str) -> Deck | None:
        deck = cast(Deck | None, get_public_deck(deck_id))
        if deck is None or not self.get_deck_validation(deck).is_valid:
            return None
        return deck

    def get_owner_deck(self, deck_id: str, owner_id: str) -> Deck | None:
        return cast(Deck | None, get_owner_deck(deck_id, owner_id))

    def get_deck_for_viewer(self, deck_id: str, *, viewer_id: str | None) -> Deck | None:
        deck = cast(Deck | None, get_deck_for_viewer(deck_id, viewer_id=viewer_id))
        if deck is None:
            return None
        if viewer_id and str(getattr(deck.owner, "pk", "")) == viewer_id:
            return deck
        if not deck.is_public:
            return None
        return deck if self.get_deck_validation(deck).is_valid else None

    @transaction.atomic
    def create_owner_deck(
        self,
        *,
        owner_id: str,
        name: str,
        description: str | None,
        is_public: bool,
        hero_card_id: str,
        entries: list[DeckEntryInput],
    ) -> Deck:
        normalized_name = self._normalize_name(name)
        normalized_description = self._normalize_description(description)
        hero_card, normalized_entries = self._normalize_deck_payload(
            hero_card_id=hero_card_id,
            entries=entries,
        )
        deck = create_deck(
            owner_id=owner_id,
            name=normalized_name,
            description=normalized_description,
            is_public=is_public,
            hero_card=hero_card,
        )
        replace_deck_entries(deck=deck, entries=normalized_entries)
        return self.get_owner_deck(deck.id, owner_id) or deck

    @transaction.atomic
    def update_owner_deck(
        self,
        *,
        deck_id: str,
        owner_id: str,
        name: str,
        description: str | None,
        is_public: bool,
        hero_card_id: str,
        entries: list[DeckEntryInput],
    ) -> Deck | None:
        existing_deck = self.get_owner_deck(deck_id, owner_id)
        if existing_deck is None:
            return None

        normalized_name = self._normalize_name(name)
        normalized_description = self._normalize_description(description)
        hero_card, normalized_entries = self._normalize_deck_payload(
            hero_card_id=hero_card_id,
            entries=entries,
        )
        updated = update_deck(
            deck_id=deck_id,
            updates={
                "name": normalized_name,
                "description": normalized_description,
                "is_public": is_public,
                "hero_card": hero_card,
            },
        )
        if updated is None:
            return None
        replace_deck_entries(deck=updated, entries=normalized_entries)
        return self.get_owner_deck(deck_id, owner_id) or updated

    def delete_owner_deck(self, *, deck_id: str, owner_id: str) -> bool:
        return cast(bool, delete_deck(deck_id=deck_id, owner_id=owner_id))

    def get_deck_validation(self, deck: Deck) -> DeckValidationSummary:
        entries = list(cast(Any, deck).entries.all())
        issues: list[str] = []
        total_cards = 0

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

        if total_cards < MIN_MAINBOARD_CARD_COUNT or total_cards > MAX_MAINBOARD_CARD_COUNT:
            issues.append(
                f"Deck must contain between {MIN_MAINBOARD_CARD_COUNT} and {MAX_MAINBOARD_CARD_COUNT} mainboard cards."
            )

        is_valid = len(issues) == 0
        return DeckValidationSummary(
            is_valid=is_valid,
            status_label="Ready" if is_valid else "In Progress",
            total_cards=total_cards,
            unique_cards=len(entries),
            issues=issues,
        )

    def _normalize_deck_payload(
        self,
        *,
        hero_card_id: str,
        entries: list[DeckEntryInput],
    ) -> tuple[Card, list[tuple[str, int]]]:
        hero_card = get_deck_card(hero_card_id)
        if hero_card is None:
            raise ValueError("Hero card not found.")
        if not hero_card.is_hero:
            raise ValueError("Hero card must be marked as a hero.")

        ordered_entry_ids = [entry.card_id.strip() for entry in entries if entry.card_id.strip()]
        if len(ordered_entry_ids) != len(entries):
            raise ValueError("Each deck entry must reference a card.")
        if len(set(ordered_entry_ids)) != len(ordered_entry_ids):
            raise ValueError("Each card can only appear once in the mainboard entries.")

        cards_by_id = get_cards_by_ids(ordered_entry_ids)
        missing_ids = [card_id for card_id in ordered_entry_ids if card_id not in cards_by_id]
        if missing_ids:
            raise ValueError("One or more selected mainboard cards do not exist.")

        normalized_entries: list[tuple[str, int]] = []
        for entry in entries:
            card_id = entry.card_id.strip()
            quantity = int(entry.quantity)
            if quantity < 1 or quantity > MAX_DECK_COPIES:
                raise ValueError(f"Each mainboard card quantity must be between 1 and {MAX_DECK_COPIES}.")
            card = cards_by_id[card_id]
            if card.is_hero:
                raise ValueError("Hero cards cannot appear in mainboard entries.")
            if card.id == hero_card.id:
                raise ValueError("Hero card cannot also appear in the mainboard.")
            normalized_entries.append((card.id, quantity))

        return hero_card, normalized_entries

    def _normalize_name(self, name: str) -> str:
        normalized = " ".join(name.split()).strip()
        if not normalized:
            raise ValueError("Deck name is required.")
        return normalized

    def _normalize_description(self, description: str | None) -> str | None:
        if description is None:
            return None
        normalized = " ".join(description.split()).strip()
        return normalized or None
