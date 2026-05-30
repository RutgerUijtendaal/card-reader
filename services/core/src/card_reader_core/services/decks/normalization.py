from __future__ import annotations

from card_reader_core.models import Card
from card_reader_core.repositories.decks import get_cards_by_ids, get_deck_card

from .constraints import DeckConstraintEntry, DeckConstraintEvaluator
from .types import DeckEntryInput, DeckSideboardInput


class DeckPayloadNormalizer:
    def normalize_deck_payload(
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

        sideboard_entry_ids = [
            entry.card_id.strip()
            for sideboard in sideboards
            for entry in sideboard.entries
            if entry.card_id.strip()
        ]
        sideboard_missing_card_id = any(
            not entry.card_id.strip()
            for sideboard in sideboards
            for entry in sideboard.entries
        )
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

        normalized_entries, mainboard_constraint_entries = self._normalize_mainboard_entries(
            entries=entries,
            hero_card=hero_card,
            cards_by_id=cards_by_id,
        )
        normalized_sideboards, sideboard_constraint_entries = self._normalize_sideboards(
            sideboards=sideboards,
            hero_card=hero_card,
            cards_by_id=cards_by_id,
        )
        evaluation = DeckConstraintEvaluator().evaluate(
            hero_card=hero_card,
            entries=[*mainboard_constraint_entries, *sideboard_constraint_entries],
        )
        if evaluation.blocking_violations:
            raise ValueError(evaluation.blocking_violations[0].message)
        return hero_card, normalized_entries, normalized_sideboards

    def normalize_name(self, name: str) -> str:
        normalized = " ".join(name.split()).strip()
        if not normalized:
            raise ValueError("Deck name is required.")
        return normalized

    def normalize_description(self, description: str | None) -> str | None:
        if description is None:
            return None
        normalized = " ".join(description.split()).strip()
        return normalized or None

    def normalize_sideboard_name(self, name: str) -> str:
        normalized = " ".join(name.split()).strip()
        if not normalized:
            raise ValueError("Sideboard name is required.")
        return normalized

    def _normalize_mainboard_entries(
        self,
        *,
        entries: list[DeckEntryInput],
        hero_card: Card,
        cards_by_id: dict[str, Card],
    ) -> tuple[list[tuple[str, int]], list[DeckConstraintEntry]]:
        normalized_entries: list[tuple[str, int]] = []
        constraint_entries: list[DeckConstraintEntry] = []
        for entry in entries:
            card_id = entry.card_id.strip()
            quantity = int(entry.quantity)
            card = cards_by_id[card_id]
            if card.is_hero:
                raise ValueError("Hero cards cannot appear in mainboard entries.")
            if card.id == hero_card.id:
                raise ValueError("Hero card cannot also appear in the mainboard.")
            normalized_entries.append((card.id, quantity))
            constraint_entries.append(DeckConstraintEntry(card=card, quantity=quantity, board="mainboard"))
        return normalized_entries, constraint_entries

    def _normalize_sideboards(
        self,
        *,
        sideboards: list[DeckSideboardInput],
        hero_card: Card,
        cards_by_id: dict[str, Card],
    ) -> tuple[list[dict[str, object]], list[DeckConstraintEntry]]:
        normalized_sideboards: list[dict[str, object]] = []
        constraint_entries: list[DeckConstraintEntry] = []
        for sideboard in sideboards:
            normalized_sideboard_name = self.normalize_sideboard_name(sideboard.name)
            ordered_sideboard_entry_ids = [
                entry.card_id.strip()
                for entry in sideboard.entries
                if entry.card_id.strip()
            ]
            if len(ordered_sideboard_entry_ids) != len(sideboard.entries):
                raise ValueError("Each sideboard entry must reference a card.")
            if len(set(ordered_sideboard_entry_ids)) != len(ordered_sideboard_entry_ids):
                raise ValueError("Each card can only appear once within a sideboard.")
            normalized_sideboard_entries, sideboard_constraint_entries = self._normalize_sideboard_entries(
                entries=sideboard.entries,
                hero_card=hero_card,
                cards_by_id=cards_by_id,
            )
            constraint_entries.extend(sideboard_constraint_entries)
            normalized_sideboards.append(
                {
                    "name": normalized_sideboard_name,
                    "entries": normalized_sideboard_entries,
                }
            )
        return normalized_sideboards, constraint_entries

    def _normalize_sideboard_entries(
        self,
        *,
        entries: list[DeckEntryInput],
        hero_card: Card,
        cards_by_id: dict[str, Card],
    ) -> tuple[list[tuple[str, int]], list[DeckConstraintEntry]]:
        normalized_sideboard_entries: list[tuple[str, int]] = []
        constraint_entries: list[DeckConstraintEntry] = []
        for entry in entries:
            card_id = entry.card_id.strip()
            quantity = int(entry.quantity)
            card = cards_by_id[card_id]
            if card.is_hero or card.id == hero_card.id:
                raise ValueError("Hero cards cannot appear in sideboards.")
            normalized_sideboard_entries.append((card.id, quantity))
            constraint_entries.append(DeckConstraintEntry(card=card, quantity=quantity, board="sideboard"))
        return normalized_sideboard_entries, constraint_entries
