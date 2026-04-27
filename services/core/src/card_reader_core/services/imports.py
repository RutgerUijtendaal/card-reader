from __future__ import annotations

from pathlib import Path

import card_reader_core.repositories as repositories
from card_reader_core.models import ImportJob


class ImportService:
    def create_job(
        self,
        *,
        source_path: str,
        template_id: str,
        options: dict[str, object],
    ) -> ImportJob:
        template = repositories.get_template_by_key(key=template_id)
        if template is None:
            raise ValueError(f"Unknown template_id '{template_id}'")

        return repositories.create_import_job(
            source_path=Path(source_path),
            template_id=template_id,
            options=options,
        )
