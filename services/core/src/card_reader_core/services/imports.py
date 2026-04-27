from __future__ import annotations

from pathlib import Path

from card_reader_core.models import ImportJob
from card_reader_core.repositories.import_jobs_repository import create_import_job
from card_reader_core.repositories.templates_repository import get_template_by_key


class ImportService:
    def create_job(
        self,
        *,
        source_path: str,
        template_id: str,
        options: dict[str, object],
    ) -> ImportJob:
        template = get_template_by_key(key=template_id)
        if template is None:
            raise ValueError(f"Unknown template_id '{template_id}'")

        return create_import_job(
            source_path=Path(source_path),
            template_id=template_id,
            options=options,
        )
