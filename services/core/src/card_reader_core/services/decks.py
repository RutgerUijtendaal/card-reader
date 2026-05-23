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
MAINBOARD_CARD_COUNT = 60


@dataclass(frozen=True)
class DeckEntryInput:
    card_id: str
    quantity: int


class DeckService:
    def list_public_decks(self) -> list[Deck]:
        return cast(list[Deck], list_public_decks())

    def list_owner_decks(self, owner_id: str) -> list[Deck]:
        return cast(list[Deck], list_owner_decks(owner_id))

    def get_public_deck(self, deck_id: str) -> Deck | None:
        return cast(Deck | None, get_public_deck(deck_id))

    def get_owner_deck(self, deck_id: str, owner_id: str) -> Deck | None:
        return cast(Deck | None, get_owner_deck(deck_id, owner_id))

    def get_deck_for_viewer(self, deck_id: str, *, viewer_id: str | None) -> Deck | None:
        return cast(Deck | None, get_deck_for_viewer(deck_id, viewer_id=viewer_id))

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

        if not entries:
            raise ValueError("Deck must contain 60 mainboard cards.")

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
        total_quantity = 0
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
            total_quantity += quantity

        if total_quantity != MAINBOARD_CARD_COUNT:
            raise ValueError(f"Deck must contain exactly {MAINBOARD_CARD_COUNT} mainboard cards.")

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
