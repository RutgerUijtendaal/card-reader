from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

from django.db import IntegrityError, transaction

from card_reader_core.models import CardPool, CardRole, ImportJob
from card_reader_core.repositories.content_versions import create_next_content_version
from card_reader_core.repositories.import_jobs import (
    cancel_import_job,
    create_import_job,
    fetch_job_by_creation_key,
)
from card_reader_core.repositories.templates import get_template_by_key
from .classification import LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION, CardRoleMode


class ImportCreationKeyConflict(ValueError):
    pass


class ImportService:
    def create_job(
        self,
        *,
        source_path: str,
        template_id: str,
        options: dict[str, object],
        content_version_base: str,
        content_version_description: str,
        creation_key: str,
        creation_fingerprint: str,
        card_pool: CardPool,
        card_role_mode: CardRoleMode = "automatic",
        card_role_override: Sequence[CardRole] = (),
    ) -> tuple[ImportJob, bool]:
        existing = self.get_job_by_creation_key(creation_key=creation_key)
        if existing is not None:
            return self._matching_replay(existing, creation_fingerprint), True
        template = get_template_by_key(key=template_id)
        if template is None:
            raise ValueError(f"Unknown template_id '{template_id}'")

        try:
            with transaction.atomic():
                content_version = create_next_content_version(
                    base_version=content_version_base,
                    description=content_version_description,
                )
                job = create_import_job(
                    source_path=Path(source_path),
                    template_id=template_id,
                    options=options,
                    content_version=content_version,
                    creation_key=creation_key,
                    creation_fingerprint=creation_fingerprint,
                    card_pool=card_pool,
                    card_role_mode=card_role_mode,
                    card_role_override=card_role_override,
                    inference_policy_version=LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION,
                )
        except IntegrityError:
            existing = self.get_job_by_creation_key(creation_key=creation_key)
            if existing is None:
                raise
            return self._matching_replay(existing, creation_fingerprint), True
        return job, False

    def get_job_by_creation_key(self, *, creation_key: str) -> ImportJob | None:
        return fetch_job_by_creation_key(creation_key)

    def _matching_replay(self, job: ImportJob, fingerprint: str) -> ImportJob:
        if job.creation_fingerprint != fingerprint:
            raise ImportCreationKeyConflict(
                "This creation key has already been used for a different import payload."
            )
        return job

    def cancel_job(self, *, job_id: str) -> ImportJob | None:
        return cancel_import_job(job_id)
