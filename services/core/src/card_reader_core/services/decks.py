from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from card_reader_core.models import Card, Deck, DeckVisibility
from card_reader_core.repositories.decks_repository import (
    create_deck,
    delete_deck,
    get_cards_by_ids,
    get_deck_for_viewer,
    get_owner_deck,
    get_public_deck,
    list_owner_decks,
    list_public_decks,
    replace_mainboard_entries,
    replace_sideboards,
    update_deck,
)
from card_reader_core.repositories.decks_repository import get_deck_card

MAX_DECK_COPIES = 4
MIN_MAINBOARD_CARD_COUNT = 20
MAX_MAINBOARD_CARD_COUNT = 100
MIN_MAINBOARD_MANA_TYPE_COUNT = 3
MAX_SIDEBOARD_ENTRY_QUANTITY = 100


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


@dataclass(frozen=True)
class DeckSideboardInput:
    name: str
    entries: list[DeckEntryInput]


@dataclass(frozen=True)
class DeckTotals:
    overall_total_cards: int
    overall_unique_cards: int
    mainboard_total_cards: int
    mainboard_unique_cards: int


@dataclass(frozen=True)
class DeckUpdateInput:
    name: str | None = None
    description: str | None = None
    visibility: DeckVisibility | None = None
    hero_card_id: str | None = None
    entries: list[DeckEntryInput] | None = None
    sideboards: list[DeckSideboardInput] | None = None
    update_name: bool = False
    update_description: bool = False
    update_visibility: bool = False
    update_hero_card_id: bool = False
    update_entries: bool = False
    update_sideboards: bool = False


class DeckService:
    def list_public_decks(
        self,
        *,
        hero_query: str | None = None,
        card_query: str | None = None,
        affinity_symbol_ids: list[str] | None = None,
        affinity_symbol_match: str | None = None,
    ) -> list[Deck]:
        return [
            deck
            for deck in list_public_decks(
                hero_query=hero_query,
                card_query=card_query,
                affinity_symbol_ids=affinity_symbol_ids,
                affinity_symbol_match=affinity_symbol_match,
            )
            if self.get_deck_validation(deck).is_valid
        ]

    def list_owner_decks(self, owner_id: str) -> list[Deck]:
        return list_owner_decks(owner_id)

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
        normalized_name = self._normalize_name(name)
        normalized_description = self._normalize_description(description)
        hero_card, normalized_entries, normalized_sideboards = self._normalize_deck_payload(
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

        normalized_name = self._normalize_name(effective_name)
        normalized_description = self._normalize_description(effective_description)
        hero_card, normalized_entries, normalized_sideboards = self._normalize_deck_payload(
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

    def _normalize_deck_payload(
        self,
        *,
        hero_card_id: str,
        entries: list[DeckEntryInput],
        sideboards: list[DeckSideboardInput],
    ) -> tuple[Card, list[tuple[str, int]], list[dict[str, object]]]:
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

        sideboard_entry_ids = [entry.card_id.strip() for sideboard in sideboards for entry in sideboard.entries if entry.card_id.strip()]
        sideboard_missing_card_id = any(not entry.card_id.strip() for sideboard in sideboards for entry in sideboard.entries)
        if sideboard_missing_card_id:
            raise ValueError("Each sideboard entry must reference a card.")

        all_card_ids = list(dict.fromkeys([*ordered_entry_ids, *sideboard_entry_ids]))
        cards_by_id = get_cards_by_ids(all_card_ids)
        missing_ids = [card_id for card_id in ordered_entry_ids if card_id not in cards_by_id]
        if missing_ids:
            raise ValueError("One or more selected mainboard cards do not exist.")
        missing_sideboard_ids = [card_id for card_id in sideboard_entry_ids if card_id not in cards_by_id]
        if missing_sideboard_ids:
            raise ValueError("One or more selected sideboard cards do not exist.")

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

        normalized_sideboards: list[dict[str, object]] = []
        for sideboard in sideboards:
            normalized_sideboard_name = self._normalize_sideboard_name(sideboard.name)
            ordered_sideboard_entry_ids = [entry.card_id.strip() for entry in sideboard.entries if entry.card_id.strip()]
            if len(ordered_sideboard_entry_ids) != len(sideboard.entries):
                raise ValueError("Each sideboard entry must reference a card.")
            if len(set(ordered_sideboard_entry_ids)) != len(ordered_sideboard_entry_ids):
                raise ValueError("Each card can only appear once within a sideboard.")
            normalized_sideboard_entries: list[tuple[str, int]] = []
            for entry in sideboard.entries:
                card_id = entry.card_id.strip()
                quantity = int(entry.quantity)
                if quantity < 1 or quantity > MAX_SIDEBOARD_ENTRY_QUANTITY:
                    raise ValueError(
                        f"Each sideboard card quantity must be between 1 and {MAX_SIDEBOARD_ENTRY_QUANTITY}."
                    )
                card = cards_by_id[card_id]
                if card.is_hero or card.id == hero_card.id:
                    raise ValueError("Hero cards cannot appear in sideboards.")
                normalized_sideboard_entries.append((card.id, quantity))
            normalized_sideboards.append(
                {
                    "name": normalized_sideboard_name,
                    "entries": normalized_sideboard_entries,
                }
            )

        return hero_card, normalized_entries, normalized_sideboards

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

    def _normalize_sideboard_name(self, name: str) -> str:
        normalized = " ".join(name.split()).strip()
        if not normalized:
            raise ValueError("Sideboard name is required.")
        return normalized

    def _card_has_type(self, card: Card, type_key: str) -> bool:
        version = card.latest_version
        if version is None:
            return False
        normalized_key = type_key.strip().lower()
        return any(row.type.key.strip().lower() == normalized_key for row in version.card_version_types.all())
