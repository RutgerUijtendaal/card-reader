from __future__ import annotations

from card_reader_core.models import (
    HERO_CARD_ROLE,
    PLAYER_CARD_POOL,
    Card,
    Deck,
    DeckEntry,
    DeckSideboard,
    card_has_role,
)
from card_reader_core.repositories.decks import get_cards_by_ids, get_deck_card

from .constraints import DeckConstraintEntry, DeckConstraintEvaluator
from .types import DeckEntryInput, DeckSideboardInput


def _validate_preserved_non_player_mainboard_entries(
    *,
    entries: list[DeckEntryInput],
    existing_entries: list[DeckEntry],
) -> None:
    expected_quantities = {
        entry.card.id: int(entry.quantity)
        for entry in existing_entries
        if entry.card.card_pool != PLAYER_CARD_POOL
    }
    for entry in entries:
        expected_quantity = expected_quantities.get(entry.card_id)
        if expected_quantity is not None and int(entry.quantity) != expected_quantity:
            raise ValueError("Non-Player mainboard references can only be preserved unchanged.")


def _validate_preserved_non_player_sideboard_entries(
    *,
    sideboards: list[DeckSideboardInput],
    existing_sideboards: list[DeckSideboard],
) -> list[str | None]:
    existing_by_id = {sideboard.id: sideboard for sideboard in existing_sideboards}
    existing_by_name = _index_sideboards_by_name(existing_sideboards)
    non_player_card_ids, expected_quantities = _index_non_player_sideboard_entries(
        existing_sideboards
    )
    explicitly_referenced_source_ids = _existing_source_ids(
        sideboards,
        existing_by_id=existing_by_id,
    )
    if len(explicitly_referenced_source_ids) != len(set(explicitly_referenced_source_ids)):
        raise ValueError("Each existing sideboard can only be submitted once.")
    reserved_source_sideboard_ids = set(explicitly_referenced_source_ids)
    used_source_sideboard_ids: set[str] = set()
    resolved_source_sideboard_ids: list[str | None] = []
    for submitted_sideboard in sideboards:
        requires_source = any(
            entry.card_id in non_player_card_ids for entry in submitted_sideboard.entries
        )
        source_sideboard = _resolve_source_sideboard(
            submitted_sideboard,
            existing_by_id=existing_by_id,
            existing_by_name=existing_by_name,
            reserved_source_sideboard_ids=reserved_source_sideboard_ids,
            used_source_sideboard_ids=used_source_sideboard_ids,
            requires_source=requires_source,
        )
        resolved_source_sideboard_ids.append(
            source_sideboard.id if source_sideboard is not None else None
        )
        if source_sideboard is not None:
            used_source_sideboard_ids.add(source_sideboard.id)
        _validate_non_player_sideboard_quantities(
            submitted_sideboard,
            source_sideboard=source_sideboard,
            non_player_card_ids=non_player_card_ids,
            expected_quantities=expected_quantities,
        )
    return resolved_source_sideboard_ids


def _index_sideboards_by_name(
    sideboards: list[DeckSideboard],
) -> dict[str, list[DeckSideboard]]:
    sideboards_by_name: dict[str, list[DeckSideboard]] = {}
    for sideboard in sideboards:
        sideboards_by_name.setdefault(sideboard.name, []).append(sideboard)
    return sideboards_by_name


def _index_non_player_sideboard_entries(
    sideboards: list[DeckSideboard],
) -> tuple[set[str], dict[tuple[str, str], int]]:
    card_ids: set[str] = set()
    quantities: dict[tuple[str, str], int] = {}
    for sideboard in sideboards:
        for entry in sideboard.entries.all():
            if entry.card.card_pool == PLAYER_CARD_POOL:
                continue
            card_ids.add(entry.card.id)
            quantities[(sideboard.id, entry.card.id)] = int(entry.quantity)
    return card_ids, quantities


def _existing_source_ids(
    sideboards: list[DeckSideboardInput],
    *,
    existing_by_id: dict[str, DeckSideboard],
) -> list[str]:
    source_ids: list[str] = []
    for submitted_sideboard in sideboards:
        if submitted_sideboard.source_id is None:
            continue
        source = existing_by_id.get(submitted_sideboard.source_id)
        if source is not None:
            source_ids.append(source.id)
    return source_ids


def _validate_non_player_sideboard_quantities(
    submitted_sideboard: DeckSideboardInput,
    *,
    source_sideboard: DeckSideboard | None,
    non_player_card_ids: set[str],
    expected_quantities: dict[tuple[str, str], int],
) -> None:
    source_id = source_sideboard.id if source_sideboard is not None else ""
    for entry in submitted_sideboard.entries:
        if entry.card_id not in non_player_card_ids:
            continue
        expected_quantity = expected_quantities.get((source_id, entry.card_id))
        if expected_quantity != int(entry.quantity):
            raise ValueError(
                "Non-Player sideboard references can only be preserved unchanged."
            )


def _resolve_source_sideboard(
    submitted_sideboard: DeckSideboardInput,
    *,
    existing_by_id: dict[str, DeckSideboard],
    existing_by_name: dict[str, list[DeckSideboard]],
    reserved_source_sideboard_ids: set[str],
    used_source_sideboard_ids: set[str],
    requires_source: bool,
) -> DeckSideboard | None:
    source_sideboard = (
        existing_by_id.get(submitted_sideboard.source_id)
        if submitted_sideboard.source_id is not None
        else None
    )
    if source_sideboard is not None:
        if source_sideboard.id in used_source_sideboard_ids:
            raise ValueError("Each existing sideboard can only be submitted once.")
        return source_sideboard

    named_candidates = existing_by_name.get(submitted_sideboard.name, [])
    available_candidates = [
        sideboard
        for sideboard in named_candidates
        if sideboard.id not in used_source_sideboard_ids
        and sideboard.id not in reserved_source_sideboard_ids
    ]
    if not available_candidates:
        if named_candidates and requires_source:
            raise ValueError("Each existing sideboard can only be submitted once.")
        return None

    submitted_entries = _submitted_sideboard_entry_signature(submitted_sideboard)
    exact_candidates = [
        sideboard
        for sideboard in available_candidates
        if _stored_sideboard_entry_signature(sideboard) == submitted_entries
    ]
    return exact_candidates[0] if len(exact_candidates) == 1 else available_candidates[0]


def _submitted_sideboard_entry_signature(
    sideboard: DeckSideboardInput,
) -> list[tuple[str, int]]:
    return [
        (entry.card_id, int(entry.quantity))
        for entry in sideboard.entries
    ]


def _stored_sideboard_entry_signature(
    sideboard: DeckSideboard,
) -> list[tuple[str, int]]:
    return [
        (entry.card.id, int(entry.quantity))
        for entry in sideboard.entries.all()
    ]


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
        return self._normalize_resolved_deck_payload(
            hero_card=hero_card,
            entries=entries,
            sideboards=sideboards,
            retained_mainboard_cards_by_id={},
            retained_sideboard_cards_by_id={},
            sideboard_source_ids=[None] * len(sideboards),
        )

    def normalize_deck_update(
        self,
        *,
        existing_deck: Deck,
        hero_card_id: str,
        entries: list[DeckEntryInput],
        sideboards: list[DeckSideboardInput],
        update_hero_card_id: bool,
        update_entries: bool,
        update_sideboards: bool,
    ) -> tuple[Card, list[tuple[str, int]], list[dict[str, object]]]:
        hero_card = (
            existing_deck.hero_card
            if not update_hero_card_id or hero_card_id == existing_deck.hero_card.id
            else get_deck_card(hero_card_id)
        )
        if hero_card is None:
            raise ValueError("Hero card not found.")
        existing_mainboard_entries = list(existing_deck.entries.all())
        existing_sideboards = list(existing_deck.sideboards.all())
        retained_mainboard_cards_by_id = {
            entry.card.id: entry.card
            for entry in existing_mainboard_entries
            if not update_entries
            or entry.card.card_pool != PLAYER_CARD_POOL
        }
        retained_sideboard_cards_by_id: dict[str, Card] = {}
        for sideboard in existing_sideboards:
            for entry in sideboard.entries.all():
                should_retain = (
                    not update_sideboards
                    or entry.card.card_pool != PLAYER_CARD_POOL
                )
                if should_retain:
                    retained_sideboard_cards_by_id[entry.card.id] = entry.card
        if update_entries:
            _validate_preserved_non_player_mainboard_entries(
                entries=entries,
                existing_entries=existing_mainboard_entries,
            )
        sideboard_source_ids: list[str | None] = [None] * len(sideboards)
        if update_sideboards:
            sideboard_source_ids = _validate_preserved_non_player_sideboard_entries(
                sideboards=sideboards,
                existing_sideboards=existing_sideboards,
            )
        return self._normalize_resolved_deck_payload(
            hero_card=hero_card,
            entries=entries,
            sideboards=sideboards,
            retained_mainboard_cards_by_id=retained_mainboard_cards_by_id,
            retained_sideboard_cards_by_id=retained_sideboard_cards_by_id,
            sideboard_source_ids=sideboard_source_ids,
        )

    def _normalize_resolved_deck_payload(
        self,
        *,
        hero_card: Card,
        entries: list[DeckEntryInput],
        sideboards: list[DeckSideboardInput],
        retained_mainboard_cards_by_id: dict[str, Card],
        retained_sideboard_cards_by_id: dict[str, Card],
        sideboard_source_ids: list[str | None],
    ) -> tuple[Card, list[tuple[str, int]], list[dict[str, object]]]:
        if hero_card.card_pool == PLAYER_CARD_POOL and not card_has_role(
            hero_card,
            HERO_CARD_ROLE,
        ):
            raise ValueError("Hero card must be marked as a hero.")
        ordered_entry_ids = [entry.card_id.strip() for entry in entries if entry.card_id.strip()]
        if len(ordered_entry_ids) != len(entries):
            raise ValueError("Each deck entry must reference a card.")
        if len(set(ordered_entry_ids)) != len(ordered_entry_ids):
            raise ValueError("Each card can only appear once in the mainboard entries.")

        sideboard_entry_ids: list[str] = []
        for sideboard in sideboards:
            for entry in sideboard.entries:
                card_id = entry.card_id.strip()
                if not card_id:
                    raise ValueError("Each sideboard entry must reference a card.")
                sideboard_entry_ids.append(card_id)

        all_card_ids = list(dict.fromkeys([*ordered_entry_ids, *sideboard_entry_ids]))
        cards_by_id = get_cards_by_ids(all_card_ids)
        mainboard_cards_by_id = {**cards_by_id, **retained_mainboard_cards_by_id}
        sideboard_cards_by_id = {**cards_by_id, **retained_sideboard_cards_by_id}
        missing_ids = [card_id for card_id in ordered_entry_ids if card_id not in mainboard_cards_by_id]
        if missing_ids:
            raise ValueError("One or more selected mainboard cards do not exist.")
        missing_sideboard_ids = [
            card_id for card_id in sideboard_entry_ids if card_id not in sideboard_cards_by_id
        ]
        if missing_sideboard_ids:
            raise ValueError("One or more selected sideboard cards do not exist.")

        normalized_entries, mainboard_constraint_entries = self._normalize_mainboard_entries(
            entries=entries,
            hero_card=hero_card,
            cards_by_id=mainboard_cards_by_id,
        )
        normalized_sideboards, sideboard_constraint_entries = self._normalize_sideboards(
            sideboards=sideboards,
            hero_card=hero_card,
            cards_by_id=sideboard_cards_by_id,
            source_ids=sideboard_source_ids,
        )
        constraint_hero = (
            hero_card if hero_card.card_pool == PLAYER_CARD_POOL else None
        )
        constraint_entries = [
            entry
            for entry in [*mainboard_constraint_entries, *sideboard_constraint_entries]
            if entry.card.card_pool == PLAYER_CARD_POOL
        ]
        evaluation = DeckConstraintEvaluator().evaluate(
            hero_card=constraint_hero,
            entries=constraint_entries,
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

    def normalize_markup(self, markup: str | None) -> str | None:
        if markup is None:
            return None
        normalized = markup.replace("\r\n", "\n").replace("\r", "\n")
        return normalized if normalized.strip() else None

    def normalize_long_description(self, description: str | None) -> str | None:
        if description is None:
            return None
        normalized = description.replace("\r\n", "\n").replace("\r", "\n").strip()
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
            if card.card_pool == PLAYER_CARD_POOL:
                if card_has_role(card, HERO_CARD_ROLE):
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
        source_ids: list[str | None],
    ) -> tuple[list[dict[str, object]], list[DeckConstraintEntry]]:
        normalized_sideboards: list[dict[str, object]] = []
        constraint_entries: list[DeckConstraintEntry] = []
        for sideboard, source_id in zip(sideboards, source_ids, strict=True):
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
                    "source_id": source_id,
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
            if card.card_pool == PLAYER_CARD_POOL and (
                card_has_role(card, HERO_CARD_ROLE) or card.id == hero_card.id
            ):
                raise ValueError("Hero cards cannot appear in sideboards.")
            normalized_sideboard_entries.append((card.id, quantity))
            constraint_entries.append(DeckConstraintEntry(card=card, quantity=quantity, board="sideboard"))
        return normalized_sideboard_entries, constraint_entries
