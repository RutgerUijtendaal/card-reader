from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from templates import TemplateStore


class FileTemplateStore(TemplateStore):
    def __init__(self, templates_dir: Path) -> None:
        self._templates_dir = templates_dir

    def get_template(self, template_id: str) -> dict[str, Any]:
        template_file = self._templates_dir / f"{template_id}.json"
        if not template_file.exists():
            raise FileNotFoundError(f"Template '{template_id}' does not exist")
        return json.loads(template_file.read_text(encoding="utf-8"))
