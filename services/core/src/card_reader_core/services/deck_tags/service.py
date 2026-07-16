from __future__ import annotations

from django.db import transaction

from card_reader_core.models import Deck, DeckTag, DeckTagKind, DeckTagSuggestion
from card_reader_core.repositories.deck_tags import (
    accept_deck_tag_suggestion,
    attach_pending_suggestion,
    clear_pending_suggestion_occurrences,
    create_deck_tag,
    deck_tag_key_exists,
    delete_deck_tag,
    get_deck_tag,
    get_deck_tag_suggestion,
    get_deck_tag_suggestion_by_value,
    get_deck_tags_by_ids,
    get_or_create_deck_tag_suggestion,
    get_type_tag_by_key,
    list_deck_tag_suggestions,
    list_deck_tags,
    list_decks_for_suggestion,
    list_decks_for_tag,
    reject_deck_tag_suggestion,
    replace_deck_tag_assignments,
    update_deck_tag,
)
from card_reader_core.repositories.helpers import normalize_slug_key

from .types import AdminDeckTagCatalog, DeckTagCatalog, DeckTagDetail, DeckTagSuggestionDetail


class DeckTagService:
    def list_catalog(self) -> DeckTagCatalog:
        return {
            "roles": list_deck_tags(kind="role"),
            "types": list_deck_tags(kind="type"),
        }

    def list_admin_catalog(self) -> AdminDeckTagCatalog:
        catalog = self.list_catalog()
        return {
            **catalog,
            "suggested_types": list_deck_tag_suggestions(),
        }

    def get_tag_detail(self, *, tag_id: str) -> DeckTagDetail | None:
        tag = get_deck_tag(tag_id)
        if tag is None:
            return None
        decks = list_decks_for_tag(tag_id)
        return {"entry": tag, "linked_decks": decks, "linked_deck_count": len(decks)}

    def get_suggestion_detail(self, *, suggestion_id: str) -> DeckTagSuggestionDetail | None:
        suggestion = get_deck_tag_suggestion(suggestion_id)
        if suggestion is None:
            return None
        decks = list_decks_for_suggestion(suggestion_id)
        return {"entry": suggestion, "linked_decks": decks, "occurrence_count": len(decks)}

    def create_tag(self, *, kind: str, label: str, key: str | None = None) -> DeckTag:
        normalized_kind = self._normalize_kind(kind)
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique_key(kind=normalized_kind, key=normalized_key)
        return create_deck_tag(kind=normalized_kind, key=normalized_key, label=normalized_label)

    def update_tag(
        self,
        *,
        tag_id: str,
        kind: str | None = None,
        label: str | None = None,
        key: str | None = None,
    ) -> DeckTag | None:
        tag = get_deck_tag(tag_id)
        if tag is None:
            return None
        normalized_kind = self._normalize_kind(kind or tag.kind)
        normalized_label = self._normalize_label(label if label is not None else tag.label)
        normalized_key = self._normalize_key(
            key=key if key is not None else tag.key,
            label=normalized_label,
        )
        self._ensure_unique_key(kind=normalized_kind, key=normalized_key, exclude_id=tag.id)
        return update_deck_tag(tag=tag, kind=normalized_kind, key=normalized_key, label=normalized_label)

    def delete_tag(self, *, tag_id: str) -> bool:
        return delete_deck_tag(tag_id=tag_id)

    @transaction.atomic
    def replace_deck_metadata(
        self,
        *,
        deck: Deck,
        tag_ids: list[str],
        suggested_type_labels: list[str],
    ) -> None:
        normalized_ids = list(dict.fromkeys(tag_id.strip() for tag_id in tag_ids if tag_id.strip()))
        tags = get_deck_tags_by_ids(normalized_ids)
        if {tag.id for tag in tags} != set(normalized_ids):
            raise ValueError("One or more deck tags were not found.")

        selected_by_id = {tag.id: tag for tag in tags}
        clear_pending_suggestion_occurrences(deck=deck)
        for raw_label in suggested_type_labels:
            display_value = self._normalize_label(raw_label)
            normalized_value = self._normalize_suggestion_value(display_value)
            existing_tag = get_type_tag_by_key(normalize_slug_key(display_value))
            if existing_tag is not None:
                selected_by_id[existing_tag.id] = existing_tag
                continue

            suggestion = get_deck_tag_suggestion_by_value(normalized_value)
            if suggestion is None:
                suggestion = get_or_create_deck_tag_suggestion(
                    normalized_value=normalized_value,
                    display_value=display_value,
                )
            if suggestion.status == "rejected":
                raise ValueError(f"The deck tag suggestion '{display_value}' was rejected.")
            if suggestion.status == "accepted":
                if suggestion.accepted_tag is None:
                    raise ValueError(f"The accepted deck tag suggestion '{display_value}' no longer has a target.")
                selected_by_id[suggestion.accepted_tag.id] = suggestion.accepted_tag
                continue
            attach_pending_suggestion(deck=deck, suggestion=suggestion)

        replace_deck_tag_assignments(deck=deck, tags=list(selected_by_id.values()))

    @transaction.atomic
    def accept_suggestion_to_existing(self, *, suggestion_id: str, target_id: str) -> DeckTagSuggestion | None:
        suggestion = get_deck_tag_suggestion(suggestion_id)
        if suggestion is None:
            return None
        target = get_deck_tag(target_id)
        if target is None or target.kind != "type":
            raise ValueError("Type tag not found.")
        return accept_deck_tag_suggestion(suggestion=suggestion, tag=target)

    @transaction.atomic
    def accept_suggestion_as_new(
        self,
        *,
        suggestion_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> DeckTagSuggestion | None:
        suggestion = get_deck_tag_suggestion(suggestion_id)
        if suggestion is None:
            return None
        tag = self.create_tag(
            kind="type",
            label=label or suggestion.display_value,
            key=key,
        )
        return accept_deck_tag_suggestion(suggestion=suggestion, tag=tag)

    def reject_suggestion(self, *, suggestion_id: str) -> DeckTagSuggestion | None:
        suggestion = get_deck_tag_suggestion(suggestion_id)
        if suggestion is None:
            return None
        return reject_deck_tag_suggestion(suggestion=suggestion)

    def _ensure_unique_key(self, *, kind: DeckTagKind, key: str, exclude_id: str | None = None) -> None:
        if deck_tag_key_exists(kind=kind, key=key, exclude_id=exclude_id):
            raise ValueError(f"A {kind} deck tag with key '{key}' already exists.")

    @staticmethod
    def _normalize_kind(kind: str) -> DeckTagKind:
        normalized = kind.strip().lower()
        if normalized not in {"role", "type"}:
            raise ValueError("Deck tag kind must be role or type.")
        return normalized  # type: ignore[return-value]

    @staticmethod
    def _normalize_label(label: str) -> str:
        normalized = " ".join(label.split()).strip()
        if not normalized:
            raise ValueError("Deck tag label is required.")
        return normalized

    @staticmethod
    def _normalize_key(*, key: str | None, label: str) -> str:
        normalized = normalize_slug_key(key if key is not None and key.strip() else label)
        if not normalized:
            raise ValueError("Deck tag key is invalid.")
        return normalized

    @staticmethod
    def _normalize_suggestion_value(value: str) -> str:
        return " ".join(value.lower().split()).strip()
