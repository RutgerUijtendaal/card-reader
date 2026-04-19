from __future__ import annotations

import json

from sqlmodel import Session

import card_reader_core.repositories as repositories
from card_reader_core.models import Template


class TemplateService:
    def list_templates(self, session: Session) -> list[Template]:
        return repositories.list_templates(session)

    def get_template_by_key(self, session: Session, key: str) -> Template | None:
        return repositories.get_template_by_key(session, key=key)

    def create_template(
        self,
        session: Session,
        *,
        label: str,
        key: str | None = None,
        definition_json: str,
    ) -> Template:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique_template_key(session, key=normalized_key)
        normalized_definition_json = self._normalize_definition_json(definition_json)

        return repositories.create_template(
            session,
            key=normalized_key,
            label=normalized_label,
            definition_json=normalized_definition_json,
        )

    def update_template(
        self,
        session: Session,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        definition_json: str | None = None,
    ) -> Template | None:
        row = repositories.get_template(session, entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            normalized_key = self._normalize_key(key=key, label=current_label)
            self._ensure_unique_template_key(session, key=normalized_key, exclude_id=row.id)
            updates["key"] = normalized_key
        if definition_json is not None:
            updates["definition_json"] = self._normalize_definition_json(definition_json)

        return repositories.update_template(session, entry_id=entry_id, updates=updates)

    def delete_template(self, session: Session, *, entry_id: str) -> bool:
        return repositories.delete_template(session, entry_id=entry_id)

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

    def _ensure_unique_template_key(
        self,
        session: Session,
        *,
        key: str,
        exclude_id: str | None = None,
    ) -> None:
        if repositories.template_key_exists(session, key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _normalize_definition_json(self, definition_json: str) -> str:
        raw = definition_json.strip()
        if not raw:
            raise ValueError("definition_json is required")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("definition_json must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("definition_json must be a JSON object")
        return json.dumps(parsed)

