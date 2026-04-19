from __future__ import annotations

from typing import Any, Protocol


class TemplateStore(Protocol):
    def get_template(self, template_id: str) -> dict[str, Any]:
        ...
