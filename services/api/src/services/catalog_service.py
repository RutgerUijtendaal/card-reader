from __future__ import annotations

import json

from sqlmodel import Session

import repositories as repositories
from models import Keyword, Symbol, Tag, Type

SUPPORTED_SYMBOL_DETECTOR_TYPES = {"template"}


class CatalogService:
    def list_catalog(self, session: Session) -> dict[str, list[Keyword | Tag | Symbol | Type]]:
        return {
            "keywords": repositories.list_keywords(session),
            "tags": repositories.list_tags(session),
            "symbols": repositories.list_symbols(session),
            "types": repositories.list_types(session),
        }

    def create_keyword(self, session: Session, *, label: str, key: str | None = None) -> Keyword:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique_keyword_key(session, key=normalized_key)
        return repositories.create_keyword(session, key=normalized_key, label=normalized_label)

    def update_keyword(
        self,
        session: Session,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> Keyword | None:
        row = repositories.get_keyword(session, entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique_keyword_key(session, key=normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key

        return repositories.update_keyword(session, entry_id=entry_id, updates=updates)

    def create_tag(self, session: Session, *, label: str, key: str | None = None) -> Tag:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique_tag_key(session, key=normalized_key)
        return repositories.create_tag(session, key=normalized_key, label=normalized_label)

    def update_tag(
        self,
        session: Session,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> Tag | None:
        row = repositories.get_tag(session, entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique_tag_key(session, key=normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key

        return repositories.update_tag(session, entry_id=entry_id, updates=updates)

    def create_type(self, session: Session, *, label: str, key: str | None = None) -> Type:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique_type_key(session, key=normalized_key)
        return repositories.create_type(session, key=normalized_key, label=normalized_label)

    def update_type(
        self,
        session: Session,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
    ) -> Type | None:
        row = repositories.get_type(session, entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique_type_key(session, key=normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key

        return repositories.update_type(session, entry_id=entry_id, updates=updates)

    def create_symbol(
        self,
        session: Session,
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
        self._ensure_unique_symbol_key(session, key=normalized_key)

        self._validate_symbol_config_json(detection_config_json, reference_assets_json)
        return repositories.create_symbol(
            session,
            key=normalized_key,
            label=normalized_label,
            symbol_type=self._normalize_symbol_type(symbol_type),
            detector_type=self._normalize_detector_type(detector_type),
            detection_config_json=self._normalize_detection_config_json(detection_config_json),
            reference_assets_json=self._normalize_reference_assets_json(reference_assets_json),
            text_token=(text_token or "").strip(),
            enabled=enabled if enabled is not None else True,
        )

    def update_symbol(
        self,
        session: Session,
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
        row = repositories.get_symbol(session, entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique_symbol_key(session, key=normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key

        if symbol_type is not None:
            updates["symbol_type"] = self._normalize_symbol_type(symbol_type)
        if detector_type is not None:
            updates["detector_type"] = self._normalize_detector_type(detector_type)
        if detection_config_json is not None:
            self._validate_symbol_config_json(detection_config_json, None)
            updates["detection_config_json"] = self._normalize_detection_config_json(
                detection_config_json
            )
        if reference_assets_json is not None:
            self._validate_symbol_config_json(None, reference_assets_json)
            updates["reference_assets_json"] = self._normalize_reference_assets_json(
                reference_assets_json
            )
        if text_token is not None:
            updates["text_token"] = text_token.strip()
        if enabled is not None:
            updates["enabled"] = enabled

        return repositories.update_symbol(session, entry_id=entry_id, updates=updates)

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

    def _ensure_unique_keyword_key(
        self,
        session: Session,
        *,
        key: str,
        exclude_id: str | None = None,
    ) -> None:
        if repositories.keyword_key_exists(session, key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _ensure_unique_tag_key(
        self,
        session: Session,
        *,
        key: str,
        exclude_id: str | None = None,
    ) -> None:
        if repositories.tag_key_exists(session, key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _ensure_unique_type_key(
        self,
        session: Session,
        *,
        key: str,
        exclude_id: str | None = None,
    ) -> None:
        if repositories.type_key_exists(session, key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _ensure_unique_symbol_key(
        self,
        session: Session,
        *,
        key: str,
        exclude_id: str | None = None,
    ) -> None:
        if repositories.symbol_key_exists(session, key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _validate_symbol_config_json(
        self,
        detection_config_json: str | None,
        reference_assets_json: str | None,
    ) -> None:
        if detection_config_json is not None:
            parsed = json.loads(self._normalize_detection_config_json(detection_config_json))
            if not isinstance(parsed, dict):
                raise ValueError("detection_config_json must be a JSON object")
        if reference_assets_json is not None:
            parsed = json.loads(self._normalize_reference_assets_json(reference_assets_json))
            if not isinstance(parsed, list):
                raise ValueError("reference_assets_json must be a JSON array")
            if not all(isinstance(item, str) for item in parsed):
                raise ValueError("reference_assets_json entries must be strings")

    def _normalize_detection_config_json(self, value: str | None) -> str:
        raw = (value or "").strip()
        if not raw:
            return "{}"
        return raw

    def _normalize_reference_assets_json(self, value: str | None) -> str:
        raw = (value or "").strip()
        if not raw:
            return "[]"
        return raw

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

    def delete_keyword(self, session: Session, *, entry_id: str) -> bool:
        return repositories.delete_keyword(session, entry_id=entry_id)

    def delete_tag(self, session: Session, *, entry_id: str) -> bool:
        return repositories.delete_tag(session, entry_id=entry_id)

    def delete_type(self, session: Session, *, entry_id: str) -> bool:
        return repositories.delete_type(session, entry_id=entry_id)

    def delete_symbol(self, session: Session, *, entry_id: str) -> bool:
        return repositories.delete_symbol(session, entry_id=entry_id)
