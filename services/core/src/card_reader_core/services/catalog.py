from __future__ import annotations

import json
from typing import TypedDict

from django.db import transaction

from card_reader_core.models import (
    CardVersion,
    CardVersionImage,
    Keyword,
    MetadataSuggestion,
    Symbol,
    Tag,
    Type,
    now_utc,
)
from card_reader_core.repositories.cards_repository import decode_field_sources
from card_reader_core.repositories.helpers import normalize_slug_key
from card_reader_core.repositories.metadata_repository import (
    MetadataSuggestionListRow,
    append_metadata_identifier,
    create_keyword,
    create_symbol,
    create_tag,
    create_type,
    delete_keyword,
    delete_symbol,
    delete_tag,
    delete_type,
    get_keyword,
    get_metadata_suggestion,
    get_symbol,
    get_tag,
    get_type,
    get_tags_for_card_version,
    get_types_for_card_version,
    keyword_key_exists,
    list_card_version_suggestion_occurrences,
    list_keywords_with_linked_card_counts,
    list_latest_versions_for_keyword_detail,
    list_latest_versions_for_symbol_detail,
    list_latest_versions_for_tag_detail,
    list_latest_versions_for_type_detail,
    list_metadata_suggestions,
    list_symbols_with_linked_card_counts,
    list_tags_with_linked_card_counts,
    list_types_with_linked_card_counts,
    replace_card_version_tags,
    replace_card_version_types,
    reject_metadata_suggestion,
    symbol_key_exists,
    tag_key_exists,
    type_key_exists,
    update_keyword,
    refresh_rule_text_for_symbol,
    update_symbol,
    update_tag,
    update_type,
)

SUPPORTED_SYMBOL_DETECTOR_TYPES = {"template"}


class CatalogData(TypedDict):
    known: "KnownCatalogData"
    suggested: "SuggestedCatalogData"


class KnownCatalogData(TypedDict):
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


class SuggestedCatalogData(TypedDict):
    tags: list["CatalogSuggestionDetail"]
    types: list["CatalogSuggestionDetail"]


class SuggestionOccurrencePreview(TypedDict):
    card_id: str
    card_label: str
    card_version_id: str
    card_version_name: str
    image_url: str | None
    source_text: str
    normalized_source_text: str


class LinkedCardPreview(TypedDict):
    card_id: str
    card_label: str
    card_version_id: str
    card_version_name: str
    image_url: str | None


class CatalogSuggestionDetail(TypedDict):
    id: str
    kind: str
    display_value: str
    normalized_value: str
    status: str
    occurrence_count: int
    accepted_tag: Tag | None
    accepted_type: Type | None
    occurrences: list[SuggestionOccurrencePreview]


class KeywordDetail(TypedDict):
    entry: Keyword
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int


class TagDetail(TypedDict):
    entry: Tag
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int


class TypeDetail(TypedDict):
    entry: Type
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int


class SymbolDetail(TypedDict):
    entry: Symbol
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int


class CatalogService:
    def list_catalog(self) -> CatalogData:
        return {
            "known": {
                "keywords": list_keywords_with_linked_card_counts(),
                "tags": list_tags_with_linked_card_counts(),
                "symbols": list_symbols_with_linked_card_counts(),
                "types": list_types_with_linked_card_counts(),
            },
            "suggested": {
                "tags": self.list_suggestions(kind="tag"),
                "types": self.list_suggestions(kind="type"),
            },
        }

    def list_suggestions(self, *, kind: str, status: str | None = None) -> list[CatalogSuggestionDetail]:
        rows = list_metadata_suggestions(kind=kind, status=status)
        return [self._suggestion_detail_from_row(row) for row in rows]

    def get_suggestion_detail(self, *, suggestion_id: str) -> CatalogSuggestionDetail | None:
        suggestion = get_metadata_suggestion(suggestion_id)
        if suggestion is None:
            return None
        occurrence_count = len(list_card_version_suggestion_occurrences(suggestion_id))
        return self._suggestion_detail(suggestion, occurrence_count=occurrence_count)

    def reject_suggestion(self, *, suggestion_id: str) -> MetadataSuggestion | None:
        return reject_metadata_suggestion(suggestion_id=suggestion_id)

    def get_keyword_detail(self, *, entry_id: str) -> KeywordDetail | None:
        entry = get_keyword(entry_id)
        if entry is None:
            return None
        linked_cards, linked_card_count = self._linked_cards_for_versions(
            *list_latest_versions_for_keyword_detail(entry_id=entry_id)
        )
        return {
            "entry": entry,
            "linked_cards": linked_cards,
            "linked_card_count": linked_card_count,
        }

    def get_tag_detail(self, *, entry_id: str) -> TagDetail | None:
        entry = get_tag(entry_id)
        if entry is None:
            return None
        linked_cards, linked_card_count = self._linked_cards_for_versions(
            *list_latest_versions_for_tag_detail(entry_id=entry_id)
        )
        return {
            "entry": entry,
            "linked_cards": linked_cards,
            "linked_card_count": linked_card_count,
        }

    def get_type_detail(self, *, entry_id: str) -> TypeDetail | None:
        entry = get_type(entry_id)
        if entry is None:
            return None
        linked_cards, linked_card_count = self._linked_cards_for_versions(
            *list_latest_versions_for_type_detail(entry_id=entry_id)
        )
        return {
            "entry": entry,
            "linked_cards": linked_cards,
            "linked_card_count": linked_card_count,
        }

    def get_symbol_detail(self, *, entry_id: str) -> SymbolDetail | None:
        entry = get_symbol(entry_id)
        if entry is None:
            return None
        linked_cards, linked_card_count = self._linked_cards_for_versions(
            *list_latest_versions_for_symbol_detail(entry_id=entry_id)
        )
        return {
            "entry": entry,
            "linked_cards": linked_cards,
            "linked_card_count": linked_card_count,
        }

    def accept_suggestion_to_existing(
        self,
        *,
        suggestion_id: str,
        target_id: str,
    ) -> MetadataSuggestion | None:
        suggestion = get_metadata_suggestion(suggestion_id)
        if suggestion is None:
            return None

        if suggestion.kind == "tag":
            target_tag = get_tag(target_id)
            if target_tag is None:
                raise ValueError("Tag not found")
            with transaction.atomic():
                append_metadata_identifier(entry=target_tag, identifier=suggestion.normalized_value)
                self._apply_suggestion_to_auto_versions(suggestion, target_tag=target_tag)
            return get_metadata_suggestion(suggestion_id)

        target_type = get_type(target_id)
        if target_type is None:
            raise ValueError("Type not found")
        with transaction.atomic():
            append_metadata_identifier(entry=target_type, identifier=suggestion.normalized_value)
            self._apply_suggestion_to_auto_versions(suggestion, target_type=target_type)
        return get_metadata_suggestion(suggestion_id)

    def accept_suggestion_as_new(
        self,
        *,
        suggestion_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> MetadataSuggestion | None:
        suggestion = get_metadata_suggestion(suggestion_id)
        if suggestion is None:
            return None

        chosen_label = self._normalize_label(label or suggestion.display_value or suggestion.normalized_value)
        with transaction.atomic():
            if suggestion.kind == "tag":
                target_tag = self.create_tag(
                    label=chosen_label,
                    key=key,
                    identifiers=[suggestion.normalized_value],
                )
                self._apply_suggestion_to_auto_versions(suggestion, target_tag=target_tag)
            else:
                target_type = self.create_type(
                    label=chosen_label,
                    key=key,
                    identifiers=[suggestion.normalized_value],
                )
                self._apply_suggestion_to_auto_versions(suggestion, target_type=target_type)
        return get_metadata_suggestion(suggestion_id)

    def create_keyword(
        self,
        *,
        label: str,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Keyword:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique("keyword", normalized_key)
        return create_keyword(
            key=normalized_key,
            label=normalized_label,
            identifiers_json=self._normalize_identifiers_json(normalized_label, identifiers),
        )

    def create_tag(
        self,
        *,
        label: str,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Tag:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique("tag", normalized_key)
        return create_tag(
            key=normalized_key,
            label=normalized_label,
            identifiers_json=self._normalize_identifiers_json(normalized_label, identifiers),
        )

    def create_type(
        self,
        *,
        label: str,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Type:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique("type", normalized_key)
        return create_type(
            key=normalized_key,
            label=normalized_label,
            identifiers_json=self._normalize_identifiers_json(normalized_label, identifiers),
        )

    def update_keyword(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Keyword | None:
        row = get_keyword(entry_id)
        if row is None:
            return None
        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique("keyword", normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key
        if identifiers is not None:
            updates["identifiers_json"] = self._normalize_identifiers_json(current_label, identifiers)
        return update_keyword(entry_id=entry_id, updates=updates)

    def update_tag(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Tag | None:
        row = get_tag(entry_id)
        if row is None:
            return None
        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique("tag", normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key
        if identifiers is not None:
            updates["identifiers_json"] = self._normalize_identifiers_json(current_label, identifiers)
        return update_tag(entry_id=entry_id, updates=updates)

    def update_type(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Type | None:
        row = get_type(entry_id)
        if row is None:
            return None
        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique("type", normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key
        if identifiers is not None:
            updates["identifiers_json"] = self._normalize_identifiers_json(current_label, identifiers)
        return update_type(entry_id=entry_id, updates=updates)

    def create_symbol(
        self,
        *,
        label: str,
        key: str | None = None,
        symbol_type: str | None = None,
        detector_type: str | None = None,
        detection_config_json: str | None = None,
        text_enrichment_json: str | None = None,
        reference_assets_json: str | None = None,
        text_token: str | None = None,
        enabled: bool | None = None,
    ) -> Symbol:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique("symbol", normalized_key)
        self._validate_symbol_config_json(detection_config_json, reference_assets_json)
        self._validate_symbol_config_json(
            text_enrichment_json,
            None,
            field_name="text_enrichment_json",
        )
        return create_symbol(
            key=normalized_key,
            label=normalized_label,
            symbol_type=self._normalize_symbol_type(symbol_type),
            detector_type=self._normalize_detector_type(detector_type),
            detection_config_json=self._normalize_object_json(detection_config_json),
            text_enrichment_json=self._normalize_object_json(text_enrichment_json),
            reference_assets_json=self._normalize_array_json(reference_assets_json),
            text_token=(text_token or "").strip(),
            enabled=enabled if enabled is not None else True,
        )

    def update_symbol(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        symbol_type: str | None = None,
        detector_type: str | None = None,
        detection_config_json: str | None = None,
        text_enrichment_json: str | None = None,
        reference_assets_json: str | None = None,
        text_token: str | None = None,
        enabled: bool | None = None,
    ) -> Symbol | None:
        row = get_symbol(entry_id)
        if row is None:
            return None
        previous_key = row.key
        previous_text_token = row.text_token

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique("symbol", normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key

        self._apply_symbol_updates(
            updates,
            symbol_type=symbol_type,
            detector_type=detector_type,
            detection_config_json=detection_config_json,
            text_enrichment_json=text_enrichment_json,
            reference_assets_json=reference_assets_json,
            text_token=text_token,
            enabled=enabled,
        )
        updated_symbol = update_symbol(entry_id=entry_id, updates=updates)
        if updated_symbol is None:
            return None

        if updated_symbol.key != previous_key or updated_symbol.text_token != previous_text_token:
            refresh_rule_text_for_symbol(
                symbol_id=updated_symbol.id,
                old_key=previous_key,
                new_key=updated_symbol.key,
            )

        return updated_symbol

    def delete_keyword(self, *, entry_id: str) -> bool:
        return delete_keyword(entry_id=entry_id)

    def delete_tag(self, *, entry_id: str) -> bool:
        return delete_tag(entry_id=entry_id)

    def delete_type(self, *, entry_id: str) -> bool:
        return delete_type(entry_id=entry_id)

    def delete_symbol(self, *, entry_id: str) -> bool:
        return delete_symbol(entry_id=entry_id)

    def _apply_symbol_updates(
        self,
        updates: dict[str, object],
        *,
        symbol_type: str | None,
        detector_type: str | None,
        detection_config_json: str | None,
        text_enrichment_json: str | None,
        reference_assets_json: str | None,
        text_token: str | None,
        enabled: bool | None,
    ) -> None:
        if symbol_type is not None:
            updates["symbol_type"] = self._normalize_symbol_type(symbol_type)
        if detector_type is not None:
            updates["detector_type"] = self._normalize_detector_type(detector_type)
        if detection_config_json is not None:
            self._validate_symbol_config_json(detection_config_json, None)
            updates["detection_config_json"] = self._normalize_object_json(
                detection_config_json,
            )
        if text_enrichment_json is not None:
            self._validate_symbol_config_json(text_enrichment_json, None, field_name="text_enrichment_json")
            updates["text_enrichment_json"] = self._normalize_object_json(
                text_enrichment_json,
                field_name="text_enrichment_json",
            )
        if reference_assets_json is not None:
            self._validate_symbol_config_json(None, reference_assets_json)
            updates["reference_assets_json"] = self._normalize_array_json(
                reference_assets_json,
            )
        if text_token is not None:
            updates["text_token"] = text_token.strip()
        if enabled is not None:
            updates["enabled"] = enabled

    def _suggestion_detail_from_row(self, row: MetadataSuggestionListRow) -> CatalogSuggestionDetail:
        return self._suggestion_detail(row.suggestion, occurrence_count=row.occurrence_count)

    def _suggestion_detail(
        self,
        suggestion: MetadataSuggestion,
        *,
        occurrence_count: int,
    ) -> CatalogSuggestionDetail:
        occurrences = list_card_version_suggestion_occurrences(suggestion.id)
        previews: list[SuggestionOccurrencePreview] = []
        for occurrence in occurrences[:5]:
            card_version = occurrence.card_version
            card = card_version.card
            image = next(iter(card_version.images.all()), None)
            previews.append(
                {
                    "card_id": card.id,
                    "card_label": card.label,
                    "card_version_id": card_version.id,
                    "card_version_name": card_version.name,
                    "image_url": self._image_url(card.id, card_version.id, image),
                    "source_text": occurrence.source_text,
                    "normalized_source_text": occurrence.normalized_source_text,
                }
            )
        return {
            "id": suggestion.id,
            "kind": suggestion.kind,
            "display_value": suggestion.display_value,
            "normalized_value": suggestion.normalized_value,
            "status": suggestion.status,
            "occurrence_count": occurrence_count,
            "accepted_tag": suggestion.accepted_tag,
            "accepted_type": suggestion.accepted_type,
            "occurrences": previews,
        }

    def _apply_suggestion_to_auto_versions(
        self,
        suggestion: MetadataSuggestion,
        *,
        target_tag: Tag | None = None,
        target_type: Type | None = None,
    ) -> None:
        if suggestion.kind == "tag" and target_tag is None:
            raise ValueError("Tag target is required")
        if suggestion.kind == "type" and target_type is None:
            raise ValueError("Type target is required")

        occurrences = list_card_version_suggestion_occurrences(suggestion.id)
        for occurrence in occurrences:
            version = occurrence.card_version
            field_sources = decode_field_sources(version.field_sources_json)
            if suggestion.kind == "tag":
                if field_sources["metadata"].get("tags") != "auto":
                    continue
                current_ids = [row.id for row in get_tags_for_card_version(version.id)]
                next_ids = [*current_ids, target_tag.id] if target_tag is not None else current_ids
                replace_card_version_tags(card_version_id=version.id, tag_ids=next_ids)
                continue

            if field_sources["metadata"].get("types") != "auto":
                continue
            current_ids = [row.id for row in get_types_for_card_version(version.id)]
            next_ids = [*current_ids, target_type.id] if target_type is not None else current_ids
            replace_card_version_types(card_version_id=version.id, type_ids=next_ids)

        suggestion.status = "accepted"
        suggestion.accepted_tag = target_tag
        suggestion.accepted_type = target_type
        suggestion.updated_at = now_utc()
        suggestion.save(update_fields=["status", "accepted_tag", "accepted_type", "updated_at"])

    def _linked_cards_for_versions(
        self,
        versions: list[CardVersion],
        linked_card_count: int,
    ) -> tuple[list[LinkedCardPreview], int]:
        previews: list[LinkedCardPreview] = []
        for version in versions:
            image = next(iter(version.images.all()), None)
            previews.append(
                {
                    "card_id": version.card.id,
                    "card_label": version.card.label,
                    "card_version_id": version.id,
                    "card_version_name": version.name,
                    "image_url": self._image_url(version.card.id, version.id, image),
                }
            )
        return previews, linked_card_count

    def _image_url(
        self,
        card_id: str,
        card_version_id: str,
        image: CardVersionImage | None,
    ) -> str | None:
        if image is None:
            return None
        return f"/cards/{card_id}/versions/{card_version_id}/image"

    def _ensure_unique(self, kind: str, key: str, exclude_id: str | None = None) -> None:
        exists_checks = {
            "keyword": keyword_key_exists,
            "tag": tag_key_exists,
            "type": type_key_exists,
            "symbol": symbol_key_exists,
        }
        exists = exists_checks[kind]
        if exists(key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _normalize_label(self, label: str) -> str:
        compact = " ".join(label.split()).strip()
        if not compact:
            raise ValueError("Label is required")
        return compact

    def _normalize_key(self, *, key: str | None, label: str) -> str:
        source = key if key is not None and key.strip() else label
        normalized = normalize_slug_key(source)
        if not normalized:
            raise ValueError("Key is invalid")
        return normalized

    def _normalize_identifiers_json(self, label: str, identifiers: list[str] | None) -> list[str]:
        normalized_identifiers = self._normalize_identifiers(label, identifiers)
        return normalized_identifiers

    def _normalize_identifiers(self, label: str, identifiers: list[str] | None) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()

        canonical_identifier = " ".join(label.split()).strip().lower()
        if canonical_identifier:
            seen.add(canonical_identifier)
            out.append(canonical_identifier)

        if identifiers is None:
            return out

        for raw_identifier in identifiers:
            compact = " ".join(str(raw_identifier).split()).strip().lower()
            if not compact or compact in seen:
                continue
            seen.add(compact)
            out.append(compact)
        return out

    def _validate_symbol_config_json(
        self,
        object_json: str | None,
        array_json: str | None,
        *,
        field_name: str = "detection_config_json",
    ) -> None:
        if object_json is not None and not isinstance(
            self._normalize_object_json(object_json, field_name=field_name),
            dict,
        ):
            raise ValueError(f"{field_name} must be a JSON object")
        if array_json is None:
            return
        parsed = self._normalize_array_json(array_json)
        if not isinstance(parsed, list):
            raise ValueError("reference_assets_json must be a JSON array")
        if not all(isinstance(item, str) for item in parsed):
            raise ValueError("reference_assets_json entries must be strings")

    def _normalize_object_json(
        self,
        value: str | None,
        *,
        field_name: str = "detection_config_json",
    ) -> dict[str, object]:
        raw = (value or "").strip() or "{}"
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_name} must be a JSON object")
        return {str(key): parsed[key] for key in parsed}

    def _normalize_array_json(self, value: str | None) -> list[str]:
        raw = (value or "").strip() or "[]"
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("reference_assets_json must be a JSON array")
        out: list[str] = []
        for item in parsed:
            if not isinstance(item, str):
                raise ValueError("reference_assets_json entries must be strings")
            compact = item.strip()
            if compact:
                out.append(compact)
        return out

    def _normalize_detector_type(self, value: str | None) -> str:
        detector_type = (value or "template").strip().lower() or "template"
        if detector_type not in SUPPORTED_SYMBOL_DETECTOR_TYPES:
            allowed = ", ".join(sorted(SUPPORTED_SYMBOL_DETECTOR_TYPES))
            raise ValueError(f"detector_type must be one of: {allowed}")
        return detector_type

    def _normalize_symbol_type(self, value: str | None) -> str:
        symbol_type = normalize_slug_key((value or "generic").strip())
        if not symbol_type:
            raise ValueError("symbol_type is invalid")
        return symbol_type
