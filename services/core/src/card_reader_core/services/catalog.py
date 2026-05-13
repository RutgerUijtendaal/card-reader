from __future__ import annotations

import json
from typing import Any, TypedDict, cast

from card_reader_core.models import Keyword, Symbol, Tag, Type
from card_reader_core.repositories.helpers import normalize_slug_key
from card_reader_core.repositories.metadata_repository import (
    create_keyword,
    create_symbol,
    create_tag,
    create_type,
    delete_keyword,
    delete_symbol,
    delete_tag,
    delete_type,
    get_keyword,
    get_symbol,
    get_tag,
    get_type,
    keyword_key_exists,
    list_keywords,
    list_symbols,
    list_tags,
    list_types,
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
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


class CatalogService:
    def list_catalog(self) -> CatalogData:
        return {
            "keywords": list_keywords(),
            "tags": list_tags(),
            "symbols": list_symbols(),
            "types": list_types(),
        }

    def create_keyword(
        self,
        *,
        label: str,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Keyword:
        return cast(
            Keyword,
            self._create_simple("keyword", label=label, key=key, identifiers=identifiers),
        )

    def create_tag(
        self,
        *,
        label: str,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Tag:
        return cast(Tag, self._create_simple("tag", label=label, key=key, identifiers=identifiers))

    def create_type(
        self,
        *,
        label: str,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Type:
        return cast(Type, self._create_simple("type", label=label, key=key, identifiers=identifiers))

    def update_keyword(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Keyword | None:
        return cast(
            Keyword | None,
            self._update_simple("keyword", entry_id=entry_id, label=label, key=key, identifiers=identifiers),
        )

    def update_tag(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Tag | None:
        return cast(
            Tag | None,
            self._update_simple("tag", entry_id=entry_id, label=label, key=key, identifiers=identifiers),
        )

    def update_type(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        identifiers: list[str] | None = None,
    ) -> Type | None:
        return cast(
            Type | None,
            self._update_simple("type", entry_id=entry_id, label=label, key=key, identifiers=identifiers),
        )

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

    def _create_simple(
        self,
        kind: str,
        *,
        label: str,
        key: str | None,
        identifiers: list[str] | None = None,
    ) -> Any:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique(kind, normalized_key)
        if kind == "keyword":
            return create_keyword(
                key=normalized_key,
                label=normalized_label,
                identifiers_json=self._normalize_identifiers_json(normalized_label, identifiers),
            )
        if kind == "tag":
            return create_tag(
                key=normalized_key,
                label=normalized_label,
                identifiers_json=self._normalize_identifiers_json(normalized_label, identifiers),
            )
        return create_type(
            key=normalized_key,
            label=normalized_label,
            identifiers_json=self._normalize_identifiers_json(normalized_label, identifiers),
        )

    def _update_simple(
        self,
        kind: str,
        *,
        entry_id: str,
        label: str | None,
        key: str | None,
        identifiers: list[str] | None = None,
    ) -> Any | None:
        getters = {
            "keyword": get_keyword,
            "tag": get_tag,
            "type": get_type,
        }
        getter = getters[kind]
        row = getter(entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique(kind, normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key
        if kind in {"keyword", "tag", "type"} and identifiers is not None:
            updates["identifiers_json"] = self._normalize_identifiers_json(current_label, identifiers)

        updaters = {
            "keyword": update_keyword,
            "tag": update_tag,
            "type": update_type,
        }
        updater = updaters[kind]
        return updater(entry_id=entry_id, updates=updates)

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
