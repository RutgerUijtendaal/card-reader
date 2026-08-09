from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from card_reader_core.models import Deck, DeckDifficulty, DeckVisibility
from card_reader_core.services.deck_tags import DeckTagService
from card_reader_core.repositories.decks import (
    DeckSummaryPage,
    create_deck,
    create_deck_creation,
    delete_deck,
    get_deck,
    get_deck_for_viewer,
    get_public_deck_summary_page_by_ids,
    get_owner_deck,
    get_owner_deck_by_creation_id,
    get_owner_deck_creation,
    get_public_deck,
    list_card_decks_for_viewer,
    list_owner_deck_summaries,
    list_owner_deck_summary_page as list_owner_deck_summary_page_query,
    list_owner_decks,
    list_public_deck_summaries,
    list_public_deck_summary_candidates,
    list_public_decks,
    replace_mainboard_entries,
    replace_sideboards,
    update_deck,
)
from .normalization import DeckPayloadNormalizer
from .types import DeckEntryInput, DeckSideboardInput, DeckTotals, DeckUpdateInput, DeckValidationSummary
from .validation import DeckValidationService


class DeckCreationDeletedError(Exception):
    """Raised when an idempotency key belongs to a deck that was deleted."""


class DeckService:
    def __init__(
        self,
        *,
        normalizer: DeckPayloadNormalizer | None = None,
        validator: DeckValidationService | None = None,
        tag_service: DeckTagService | None = None,
    ) -> None:
        self._normalizer = normalizer or DeckPayloadNormalizer()
        self._validator = validator or DeckValidationService()
        self._tag_service = tag_service or DeckTagService()

    def list_public_decks(
        self,
        *,
        search_query: str | None = None,
        hero_query: str | None = None,
        author_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
        deck_tag_ids: list[str] | None = None,
        deck_tag_exclude_ids: list[str] | None = None,
        deck_tag_match: str | None = None,
    ) -> list[Deck]:
        return [
            deck
            for deck in list_public_decks(
                search_query=search_query,
                hero_query=hero_query,
                author_query=author_query,
                card_query=card_query,
                affinity_symbol_ids=affinity_symbol_ids,
                affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
                affinity_symbol_match=affinity_symbol_match,
                deck_tag_ids=deck_tag_ids,
                deck_tag_exclude_ids=deck_tag_exclude_ids,
                deck_tag_match=deck_tag_match,
            )
            if self.get_deck_validation(deck).is_valid
        ]

    def list_owner_decks(
        self,
        owner_id: str,
        *,
        search_query: str | None = None,
        hero_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
        deck_tag_ids: list[str] | None = None,
        deck_tag_exclude_ids: list[str] | None = None,
        deck_tag_match: str | None = None,
    ) -> list[Deck]:
        return list_owner_decks(
            owner_id,
            search_query=search_query,
            hero_query=hero_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
        )

    def list_public_deck_summaries(
        self,
        *,
        search_query: str | None = None,
        hero_query: str | None = None,
        author_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
        deck_tag_ids: list[str] | None = None,
        deck_tag_exclude_ids: list[str] | None = None,
        deck_tag_match: str | None = None,
    ) -> list[Deck]:
        return [
            deck
            for deck in list_public_deck_summaries(
                search_query=search_query,
                hero_query=hero_query,
                author_query=author_query,
                card_query=card_query,
                affinity_symbol_ids=affinity_symbol_ids,
                affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
                affinity_symbol_match=affinity_symbol_match,
                deck_tag_ids=deck_tag_ids,
                deck_tag_exclude_ids=deck_tag_exclude_ids,
                deck_tag_match=deck_tag_match,
            )
            if self.get_deck_validation(deck).is_valid
        ]

    def list_owner_deck_summaries(
        self,
        owner_id: str,
        *,
        search_query: str | None = None,
        hero_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
        deck_tag_ids: list[str] | None = None,
        deck_tag_exclude_ids: list[str] | None = None,
        deck_tag_match: str | None = None,
    ) -> list[Deck]:
        return list_owner_deck_summaries(
            owner_id,
            search_query=search_query,
            hero_query=hero_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
        )

    def list_public_deck_summary_page(
        self,
        *,
        page: int,
        page_size: int,
        snapshot_at: datetime | None = None,
        search_query: str | None = None,
        hero_query: str | None = None,
        author_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
        deck_tag_ids: list[str] | None = None,
        deck_tag_exclude_ids: list[str] | None = None,
        deck_tag_match: str | None = None,
    ) -> DeckSummaryPage:
        effective_snapshot_at = snapshot_at or timezone.now()
        candidates = list_public_deck_summary_candidates(
            snapshot_at=effective_snapshot_at,
            search_query=search_query,
            hero_query=hero_query,
            author_query=author_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
        )
        valid_deck_ids = [deck.id for deck in candidates if self.get_deck_validation(deck).is_valid]
        return get_public_deck_summary_page_by_ids(
            valid_deck_ids,
            page=page,
            page_size=page_size,
            snapshot_at=effective_snapshot_at,
        )

    def list_owner_deck_summary_page(
        self,
        owner_id: str,
        *,
        page: int,
        page_size: int,
        snapshot_at: datetime | None = None,
        search_query: str | None = None,
        hero_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_exclude_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
        deck_tag_ids: list[str] | None = None,
        deck_tag_exclude_ids: list[str] | None = None,
        deck_tag_match: str | None = None,
    ) -> DeckSummaryPage:
        return list_owner_deck_summary_page_query(
            owner_id,
            page=page,
            page_size=page_size,
            snapshot_at=snapshot_at,
            search_query=search_query,
            hero_query=hero_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
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

    def get_owner_deck_by_creation_id(self, owner_id: str, client_creation_id: UUID) -> Deck | None:
        deck, _ = self.get_owner_deck_creation_result(owner_id, client_creation_id)
        return deck

    def get_owner_deck_creation_result(
        self,
        owner_id: str,
        client_creation_id: UUID,
    ) -> tuple[Deck | None, bool]:
        creation = get_owner_deck_creation(owner_id, client_creation_id)
        if creation is None:
            legacy_deck = get_owner_deck_by_creation_id(owner_id, client_creation_id)
            return legacy_deck, legacy_deck is not None
        if creation.deck_id is None:
            return None, True
        return self.get_owner_deck(str(creation.deck_id), owner_id), True

    def get_deck(self, deck_id: str) -> Deck | None:
        return get_deck(deck_id)

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
        long_description: str | None = None,
        difficulty: DeckDifficulty | None = None,
        tag_ids: list[str] | None = None,
        suggested_type_labels: list[str] | None = None,
    ) -> Deck:
        return self._create_owner_deck(
            owner_id=owner_id,
            name=name,
            description=description,
            visibility=visibility,
            hero_card_id=hero_card_id,
            entries=entries,
            sideboards=sideboards,
            long_description=long_description,
            difficulty=difficulty,
            tag_ids=tag_ids,
            suggested_type_labels=suggested_type_labels,
        )

    def create_owner_deck_idempotently(
        self,
        *,
        owner_id: str,
        client_creation_id: UUID,
        name: str,
        description: str | None,
        visibility: DeckVisibility,
        hero_card_id: str,
        entries: list[DeckEntryInput],
        sideboards: list[DeckSideboardInput],
        long_description: str | None = None,
        difficulty: DeckDifficulty | None = None,
        tag_ids: list[str] | None = None,
        suggested_type_labels: list[str] | None = None,
    ) -> tuple[Deck, bool]:
        existing, key_used = self.get_owner_deck_creation_result(owner_id, client_creation_id)
        if key_used and existing is None:
            raise DeckCreationDeletedError
        if existing is not None:
            return existing, False
        try:
            with transaction.atomic():
                deck = self._create_owner_deck(
                    owner_id=owner_id,
                    client_creation_id=client_creation_id,
                    name=name,
                    description=description,
                    visibility=visibility,
                    hero_card_id=hero_card_id,
                    entries=entries,
                    sideboards=sideboards,
                    long_description=long_description,
                    difficulty=difficulty,
                    tag_ids=tag_ids,
                    suggested_type_labels=suggested_type_labels,
                )
                create_deck_creation(
                    owner_id=owner_id,
                    client_creation_id=client_creation_id,
                    deck=deck,
                )
        except IntegrityError:
            existing, key_used = self.get_owner_deck_creation_result(owner_id, client_creation_id)
            if key_used and existing is None:
                raise DeckCreationDeletedError from None
            if existing is None:
                raise
            return existing, False
        return deck, True

    @transaction.atomic
    def _create_owner_deck(
        self,
        *,
        owner_id: str,
        name: str,
        description: str | None,
        visibility: DeckVisibility,
        hero_card_id: str,
        entries: list[DeckEntryInput],
        sideboards: list[DeckSideboardInput],
        long_description: str | None = None,
        difficulty: DeckDifficulty | None = None,
        tag_ids: list[str] | None = None,
        suggested_type_labels: list[str] | None = None,
        client_creation_id: UUID | None = None,
    ) -> Deck:
        normalized_name = self._normalizer.normalize_name(name)
        normalized_description = self._normalizer.normalize_description(description)
        normalized_long_description = self._normalizer.normalize_long_description(long_description)
        hero_card, normalized_entries, normalized_sideboards = self._normalizer.normalize_deck_payload(
            hero_card_id=hero_card_id,
            entries=entries,
            sideboards=sideboards,
        )
        deck = create_deck(
            owner_id=owner_id,
            name=normalized_name,
            description=normalized_description,
            long_description=normalized_long_description,
            difficulty=difficulty,
            visibility=visibility,
            hero_card=hero_card,
            client_creation_id=client_creation_id,
        )
        replace_mainboard_entries(deck=deck, entries=normalized_entries)
        replace_sideboards(deck=deck, sideboards=normalized_sideboards)
        self._tag_service.replace_deck_metadata(
            deck=deck,
            tag_ids=tag_ids or [],
            suggested_type_labels=suggested_type_labels or [],
        )
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
        return self._update_deck(existing_deck=existing_deck, updates=updates)

    @transaction.atomic
    def update_deck(
        self,
        *,
        deck_id: str,
        updates: DeckUpdateInput,
    ) -> Deck | None:
        existing_deck = self.get_deck(deck_id)
        if existing_deck is None:
            return None
        return self._update_deck(existing_deck=existing_deck, updates=updates)

    def _update_deck(self, *, existing_deck: Deck, updates: DeckUpdateInput) -> Deck | None:
        deck_id = existing_deck.id
        effective_name = existing_deck.name if not updates.update_name else updates.name
        effective_description = existing_deck.description if not updates.update_description else updates.description
        effective_long_description = (
            existing_deck.long_description
            if not updates.update_long_description
            else updates.long_description
        )
        effective_difficulty = (
            existing_deck.difficulty if not updates.update_difficulty else updates.difficulty
        )
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
        normalized_long_description = self._normalizer.normalize_long_description(effective_long_description)
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
                "long_description": normalized_long_description,
                "difficulty": effective_difficulty,
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
        if updates.update_tags:
            self._replace_deck_tags(
                deck=updated,
                source_deck=existing_deck,
                tag_ids=updates.tag_ids,
                suggested_type_labels=updates.suggested_type_labels,
            )
        return self.get_deck(deck_id) or updated

    def delete_owner_deck(self, *, deck_id: str, owner_id: str) -> bool:
        return delete_deck(deck_id=deck_id, owner_id=owner_id)

    def get_deck_validation(self, deck: Deck) -> DeckValidationSummary:
        return self._validator.get_deck_validation(deck)

    def get_deck_totals(self, deck: Deck) -> DeckTotals:
        return self._validator.get_deck_totals(deck)

    def _replace_deck_tags(
        self,
        *,
        deck: Deck,
        source_deck: Deck,
        tag_ids: list[str] | None,
        suggested_type_labels: list[str] | None,
    ) -> None:
        effective_tag_ids = (
            tag_ids
            if tag_ids is not None
            else [assignment.tag.id for assignment in source_deck.tag_assignments.all()]
        )
        effective_suggested_type_labels = (
            suggested_type_labels
            if suggested_type_labels is not None
            else [
                occurrence.suggestion.display_value
                for occurrence in source_deck.tag_suggestion_occurrences.all()
            ]
        )
        self._tag_service.replace_deck_metadata(
            deck=deck,
            tag_ids=effective_tag_ids,
            suggested_type_labels=effective_suggested_type_labels,
        )
