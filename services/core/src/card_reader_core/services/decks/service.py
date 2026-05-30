from __future__ import annotations

from django.db import transaction

from card_reader_core.models import Deck, DeckVisibility
from card_reader_core.repositories.decks import (
    create_deck,
    delete_deck,
    get_deck_for_viewer,
    get_owner_deck,
    get_public_deck,
    list_card_decks_for_viewer,
    list_owner_decks,
    list_public_decks,
    replace_mainboard_entries,
    replace_sideboards,
    update_deck,
)
from .normalization import DeckPayloadNormalizer
from .types import DeckEntryInput, DeckSideboardInput, DeckTotals, DeckUpdateInput, DeckValidationSummary
from .validation import DeckValidationService


class DeckService:
    def __init__(
        self,
        *,
        normalizer: DeckPayloadNormalizer | None = None,
        validator: DeckValidationService | None = None,
    ) -> None:
        self._normalizer = normalizer or DeckPayloadNormalizer()
        self._validator = validator or DeckValidationService()

    def list_public_decks(
        self,
        *,
        hero_query: str | None = None,
        author_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
    ) -> list[Deck]:
        return [
            deck
            for deck in list_public_decks(
                hero_query=hero_query,
                author_query=author_query,
                card_query=card_query,
                affinity_symbol_ids=affinity_symbol_ids,
                affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
                affinity_symbol_match=affinity_symbol_match,
            )
            if self.get_deck_validation(deck).is_valid
        ]

    def list_owner_decks(
        self,
        owner_id: str,
        *,
        hero_query: str | None = None,
        author_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
    ) -> list[Deck]:
        return list_owner_decks(
            owner_id,
            hero_query=hero_query,
            author_query=author_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
        )

    def list_card_decks_for_viewer(self, card_id: str, *, viewer_id: str | None = None) -> list[Deck]:
        decks = list_card_decks_for_viewer(card_id, viewer_id=viewer_id)
        return [
            deck
            for deck in decks
            if (viewer_id and str(getattr(deck.owner, "pk", "")) == viewer_id)
            or (deck.visibility == "public" and self.get_deck_validation(deck).is_valid)
        ]

    def get_public_deck(self, deck_id: str) -> Deck | None:
        deck = get_public_deck(deck_id)
        if deck is None or not self.get_deck_validation(deck).is_valid:
            return None
        return deck

    def get_owner_deck(self, deck_id: str, owner_id: str) -> Deck | None:
        return get_owner_deck(deck_id, owner_id)

    def get_deck_for_viewer(self, deck_id: str, *, viewer_id: str | None) -> Deck | None:
        deck = get_deck_for_viewer(deck_id, viewer_id=viewer_id)
        if deck is None:
            return None
        if viewer_id and str(getattr(deck.owner, "pk", "")) == viewer_id:
            return deck
        if deck.visibility == "private":
            return None
        return deck if self.get_deck_validation(deck).is_valid else None

    @transaction.atomic
    def create_owner_deck(
        self,
        *,
        owner_id: str,
        name: str,
        description: str | None,
        visibility: DeckVisibility,
        hero_card_id: str,
        entries: list[DeckEntryInput],
        sideboards: list[DeckSideboardInput],
    ) -> Deck:
        normalized_name = self._normalizer.normalize_name(name)
        normalized_description = self._normalizer.normalize_description(description)
        hero_card, normalized_entries, normalized_sideboards = self._normalizer.normalize_deck_payload(
            hero_card_id=hero_card_id,
            entries=entries,
            sideboards=sideboards,
        )
        deck = create_deck(
            owner_id=owner_id,
            name=normalized_name,
            description=normalized_description,
            visibility=visibility,
            hero_card=hero_card,
        )
        replace_mainboard_entries(deck=deck, entries=normalized_entries)
        replace_sideboards(deck=deck, sideboards=normalized_sideboards)
        return self.get_owner_deck(deck.id, owner_id) or deck

    @transaction.atomic
    def update_owner_deck(
        self,
        *,
        deck_id: str,
        owner_id: str,
        updates: DeckUpdateInput,
    ) -> Deck | None:
        existing_deck = self.get_owner_deck(deck_id, owner_id)
        if existing_deck is None:
            return None

        effective_name = existing_deck.name if not updates.update_name else updates.name
        effective_description = existing_deck.description if not updates.update_description else updates.description
        effective_visibility = existing_deck.visibility if not updates.update_visibility else updates.visibility
        effective_hero_card_id = existing_deck.hero_card.id if not updates.update_hero_card_id else updates.hero_card_id
        effective_entries = (
            [
                DeckEntryInput(card_id=entry.card.id, quantity=int(entry.quantity))
                for entry in existing_deck.entries.all()
            ]
            if not updates.update_entries
            else updates.entries
        )
        effective_sideboards = (
            [
                DeckSideboardInput(
                    name=sideboard.name,
                    entries=[
                        DeckEntryInput(card_id=entry.card.id, quantity=int(entry.quantity))
                        for entry in sideboard.entries.all()
                    ],
                )
                for sideboard in existing_deck.sideboards.all()
            ]
            if not updates.update_sideboards
            else updates.sideboards
        )

        if effective_name is None:
            raise ValueError("Deck name is required.")
        if effective_visibility is None:
            raise ValueError("Deck visibility is required.")
        if effective_hero_card_id is None:
            raise ValueError("Hero card is required.")
        if effective_entries is None:
            raise ValueError("Deck entries are required.")
        if effective_sideboards is None:
            raise ValueError("Sideboards are required.")

        normalized_name = self._normalizer.normalize_name(effective_name)
        normalized_description = self._normalizer.normalize_description(effective_description)
        hero_card, normalized_entries, normalized_sideboards = self._normalizer.normalize_deck_payload(
            hero_card_id=effective_hero_card_id,
            entries=effective_entries,
            sideboards=effective_sideboards,
        )
        updated = update_deck(
            deck_id=deck_id,
            updates={
                "name": normalized_name,
                "description": normalized_description,
                "visibility": effective_visibility,
                "hero_card": hero_card,
            },
        )
        if updated is None:
            return None
        if updates.update_entries:
            replace_mainboard_entries(deck=updated, entries=normalized_entries)
        if updates.update_sideboards:
            replace_sideboards(deck=updated, sideboards=normalized_sideboards)
        return self.get_owner_deck(deck_id, owner_id) or updated

    def delete_owner_deck(self, *, deck_id: str, owner_id: str) -> bool:
        return delete_deck(deck_id=deck_id, owner_id=owner_id)

    def get_deck_validation(self, deck: Deck) -> DeckValidationSummary:
        return self._validator.get_deck_validation(deck)

    def get_deck_totals(self, deck: Deck) -> DeckTotals:
        return self._validator.get_deck_totals(deck)
