from __future__ import annotations

from pathlib import Path

from card_reader_core.models import ImportJob
from card_reader_core.repositories.content_versions import create_next_content_version
from card_reader_core.repositories.import_jobs import cancel_import_job, create_import_job
from card_reader_core.repositories.templates import get_template_by_key


class ImportService:
    def create_job(
        self,
        *,
        source_path: str,
        template_id: str,
        options: dict[str, object],
        content_version_base: str,
        content_version_description: str,
    ) -> ImportJob:
        template = get_template_by_key(key=template_id)
        if template is None:
            raise ValueError(f"Unknown template_id '{template_id}'")

        content_version = create_next_content_version(
            base_version=content_version_base,
            description=content_version_description,
        )
        return create_import_job(
            source_path=Path(source_path),
            template_id=template_id,
            options=options,
            content_version=content_version,
        )

    def cancel_job(self, *, job_id: str) -> ImportJob | None:
        return cancel_import_job(job_id)
