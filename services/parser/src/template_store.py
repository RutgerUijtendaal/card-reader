from __future__ import annotations

import json
from typing import Any

from database.connection import get_session
from repositories import get_template_by_key
from templates import TemplateStore


class DatabaseTemplateStore(TemplateStore):
    def get_template(self, template_id: str) -> dict[str, Any]:
        with get_session() as session:
            template = get_template_by_key(session, key=template_id)
        if template is None:
            raise FileNotFoundError(f"Template '{template_id}' does not exist")

        try:
            parsed = json.loads(template.definition_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Template '{template_id}' has invalid definition_json") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"Template '{template_id}' definition_json must be an object")
        return parsed
