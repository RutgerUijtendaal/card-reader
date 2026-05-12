from __future__ import annotations

import json
from typing import Any

from card_reader_core.models import Template
from card_reader_core.repositories.helpers import normalize_slug_key
from card_reader_core.repositories.templates_repository import (
    create_template,
    delete_template,
    get_template,
    get_template_by_key,
    list_templates,
    template_key_exists,
    update_template,
)


class TemplateService:
    def list_templates(self) -> list[Template]:
        return list_templates()

    def get_template_by_key(self, key: str) -> Template | None:
        return get_template_by_key(key=key)

    def get_template_definition(self, key: str) -> dict[str, Any]:
        row = self.get_template_by_key(key)
        if row is None:
            raise FileNotFoundError(f"Template '{key}' does not exist")

        if isinstance(row.definition_json, str):
            return self._normalize_definition_json(row.definition_json)
        if not isinstance(row.definition_json, dict):
            raise ValueError(f"Template '{key}' definition_json must be a JSON object")
        return row.definition_json

    def create_template(
        self,
        *,
        label: str,
        key: str | None = None,
        definition_json: str,
    ) -> Template:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique_template_key(normalized_key)
        return create_template(
            key=normalized_key,
            label=normalized_label,
            definition_json=self._normalize_definition_json(definition_json),
        )

    def update_template(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        definition_json: str | None = None,
    ) -> Template | None:
        row = get_template(entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique_template_key(normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key
        if definition_json is not None:
            updates["definition_json"] = self._normalize_definition_json(definition_json)

        return update_template(entry_id=entry_id, updates=updates)

    def delete_template(self, *, entry_id: str) -> bool:
        return delete_template(entry_id=entry_id)

    def _ensure_unique_template_key(self, key: str, exclude_id: str | None = None) -> None:
        if template_key_exists(key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _normalize_key(self, *, key: str | None, label: str) -> str:
        source = key if key is not None and key.strip() else label
        normalized = normalize_slug_key(source)
        if not normalized:
            raise ValueError("Key is invalid")
        return normalized

    def _normalize_label(self, label: str) -> str:
        compact = " ".join(label.split()).strip()
        if not compact:
            raise ValueError("Label is required")
        return compact

    def _normalize_definition_json(self, definition_json: str) -> dict[str, Any]:
        raw = definition_json.strip()
        if not raw:
            raise ValueError("definition_json is required")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("definition_json must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("definition_json must be a JSON object")
        return parsed
