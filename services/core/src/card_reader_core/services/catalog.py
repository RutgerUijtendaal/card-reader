from __future__ import annotations

import json
from typing import Any, TypedDict, cast

import card_reader_core.repositories as repositories
from card_reader_core.models import Keyword, Symbol, Tag, Type

SUPPORTED_SYMBOL_DETECTOR_TYPES = {"template"}


class CatalogData(TypedDict):
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


class CatalogService:
    def list_catalog(self) -> CatalogData:
        return {
            "keywords": repositories.list_keywords(None),
            "tags": repositories.list_tags(None),
            "symbols": repositories.list_symbols(None),
            "types": repositories.list_types(None),
        }

    def create_keyword(self, *, label: str, key: str | None = None) -> Keyword:
        return cast(Keyword, self._create_simple("keyword", label=label, key=key))

    def create_tag(self, *, label: str, key: str | None = None) -> Tag:
        return cast(Tag, self._create_simple("tag", label=label, key=key))

    def create_type(self, *, label: str, key: str | None = None) -> Type:
        return cast(Type, self._create_simple("type", label=label, key=key))

    def update_keyword(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> Keyword | None:
        return cast(Keyword | None, self._update_simple("keyword", entry_id=entry_id, label=label, key=key))

    def update_tag(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> Tag | None:
        return cast(Tag | None, self._update_simple("tag", entry_id=entry_id, label=label, key=key))

    def update_type(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> Type | None:
        return cast(Type | None, self._update_simple("type", entry_id=entry_id, label=label, key=key))

    def create_symbol(
        self,
        *,
        label: str,
        key: str | None = None,
        symbol_type: str | None = None,
        detector_type: str | None = None,
        detection_config_json: str | None = None,
        reference_assets_json: str | None = None,
        text_token: str | None = None,
        enabled: bool | None = None,
    ) -> Symbol:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique("symbol", normalized_key)
        self._validate_symbol_config_json(detection_config_json, reference_assets_json)
        return repositories.create_symbol(
            None,
            key=normalized_key,
            label=normalized_label,
            symbol_type=self._normalize_symbol_type(symbol_type),
            detector_type=self._normalize_detector_type(detector_type),
            detection_config_json=self._normalize_object_json(detection_config_json),
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
        reference_assets_json: str | None = None,
        text_token: str | None = None,
        enabled: bool | None = None,
    ) -> Symbol | None:
        row = repositories.get_symbol(None, entry_id)
        if row is None:
            return None

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
            reference_assets_json=reference_assets_json,
            text_token=text_token,
            enabled=enabled,
        )
        return repositories.update_symbol(None, entry_id=entry_id, updates=updates)

    def delete_keyword(self, *, entry_id: str) -> bool:
        return repositories.delete_keyword(None, entry_id=entry_id)

    def delete_tag(self, *, entry_id: str) -> bool:
        return repositories.delete_tag(None, entry_id=entry_id)

    def delete_type(self, *, entry_id: str) -> bool:
        return repositories.delete_type(None, entry_id=entry_id)

    def delete_symbol(self, *, entry_id: str) -> bool:
        return repositories.delete_symbol(None, entry_id=entry_id)

    def _create_simple(self, kind: str, *, label: str, key: str | None) -> Any:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique(kind, normalized_key)
        return getattr(repositories, f"create_{kind}")(
            None,
            key=normalized_key,
            label=normalized_label,
        )

    def _update_simple(
        self,
        kind: str,
        *,
        entry_id: str,
        label: str | None,
        key: str | None,
    ) -> Any | None:
        getter = getattr(repositories, f"get_{kind}")
        row = getter(None, entry_id)
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

        updater = getattr(repositories, f"update_{kind}")
        return updater(None, entry_id=entry_id, updates=updates)

    def _apply_symbol_updates(
        self,
        updates: dict[str, object],
        *,
        symbol_type: str | None,
        detector_type: str | None,
        detection_config_json: str | None,
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
        exists = getattr(repositories, f"{kind}_key_exists")
        if exists(None, key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _normalize_label(self, label: str) -> str:
        compact = " ".join(label.split()).strip()
        if not compact:
            raise ValueError("Label is required")
        return compact

    def _normalize_key(self, *, key: str | None, label: str) -> str:
        source = key if key is not None and key.strip() else label
        normalized = repositories.normalize_slug_key(source)
        if not normalized:
            raise ValueError("Key is invalid")
        return normalized

    def _validate_symbol_config_json(self, object_json: str | None, array_json: str | None) -> None:
        if object_json is not None and not isinstance(json.loads(self._normalize_object_json(object_json)), dict):
            raise ValueError("detection_config_json must be a JSON object")
        if array_json is None:
            return
        parsed = json.loads(self._normalize_array_json(array_json))
        if not isinstance(parsed, list):
            raise ValueError("reference_assets_json must be a JSON array")
        if not all(isinstance(item, str) for item in parsed):
            raise ValueError("reference_assets_json entries must be strings")

    def _normalize_object_json(self, value: str | None) -> str:
        return (value or "").strip() or "{}"

    def _normalize_array_json(self, value: str | None) -> str:
        return (value or "").strip() or "[]"

    def _normalize_detector_type(self, value: str | None) -> str:
        detector_type = (value or "template").strip().lower() or "template"
        if detector_type not in SUPPORTED_SYMBOL_DETECTOR_TYPES:
            allowed = ", ".join(sorted(SUPPORTED_SYMBOL_DETECTOR_TYPES))
            raise ValueError(f"detector_type must be one of: {allowed}")
        return detector_type

    def _normalize_symbol_type(self, value: str | None) -> str:
        symbol_type = repositories.normalize_slug_key((value or "generic").strip())
        if not symbol_type:
            raise ValueError("symbol_type is invalid")
        return symbol_type
