from __future__ import annotations

from pathlib import Path

from sqlmodel import Session

import repositories as repositories
from models import ImportJob


class ImportService:
    def create_job(
        self,
        session: Session,
        *,
        source_path: str,
        template_id: str,
        options: dict[str, object],
    ) -> ImportJob:
        template = repositories.get_template_by_key(session, key=template_id)
        if template is None:
            raise ValueError(f"Unknown template_id '{template_id}'")

        return repositories.create_import_job(
            session,
            source_path=Path(source_path),
            template_id=template_id,
            options=options,
        )
