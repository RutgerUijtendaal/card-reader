from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

from django.db import IntegrityError, transaction

from card_reader_core.models import CardFaction, CardPool, CardRole, ImportJob
from card_reader_core.imports import ImportJobCreationResult, ImportJobInputValidationError
from card_reader_core.repositories.content_versions import (
    create_next_content_version,
    normalize_description,
    parse_base_version,
)
from card_reader_core.repositories.import_jobs import (
    cancel_import_job,
    create_import_job,
    fetch_job_by_creation_key,
    prepare_import_job_inputs,
)
from .classification import CardClassificationMode


class ImportCreationKeyConflict(ValueError):
    pass


class ImportCreationRejected(ValueError):
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
        card_role_mode: CardClassificationMode = "automatic",
        card_role_override: Sequence[CardRole] = (),
        card_faction_mode: CardClassificationMode = "automatic",
        card_faction_override: Sequence[CardFaction] = (),
    ) -> ImportJobCreationResult:
        existing = self.get_job_by_creation_key(creation_key=creation_key)
        if existing is not None:
            return ImportJobCreationResult(
                job=self._matching_replay(existing, creation_fingerprint),
                outcome="replayed",
            )
        self.prevalidate_job_creation(
            template_id=template_id,
            content_version_base=content_version_base,
            content_version_description=content_version_description,
            card_pool=card_pool,
            card_role_mode=card_role_mode,
            card_role_override=card_role_override,
            card_faction_mode=card_faction_mode,
            card_faction_override=card_faction_override,
        )

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
                    card_faction_mode=card_faction_mode,
                    card_faction_override=card_faction_override,
                )
        except ImportJobInputValidationError as exc:
            raise ImportCreationRejected(str(exc)) from exc
        except IntegrityError:
            existing = self.get_job_by_creation_key(creation_key=creation_key)
            if existing is None:
                raise
            return ImportJobCreationResult(
                job=self._matching_replay(existing, creation_fingerprint),
                outcome="replayed",
            )
        return ImportJobCreationResult(job=job, outcome="created")

    def prevalidate_job_creation(
        self,
        *,
        template_id: str,
        content_version_base: str,
        content_version_description: str,
        card_pool: CardPool,
        card_role_mode: CardClassificationMode,
        card_role_override: Sequence[CardRole],
        card_faction_mode: CardClassificationMode,
        card_faction_override: Sequence[CardFaction],
    ) -> None:
        try:
            parse_base_version(content_version_base)
            normalize_description(content_version_description)
            prepare_import_job_inputs(
                template_id=template_id,
                card_pool=card_pool,
                card_role_mode=card_role_mode,
                card_role_override=card_role_override,
                card_faction_mode=card_faction_mode,
                card_faction_override=card_faction_override,
            )
        except ValueError as exc:
            raise ImportCreationRejected(str(exc)) from exc

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
