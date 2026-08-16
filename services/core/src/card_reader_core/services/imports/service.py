from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

from django.db import IntegrityError, transaction

from card_reader_core.models import CardFaction, CardPool, CardRole, ImportClassificationMode, ImportJob
from card_reader_core.metadata import ManaFamily
from card_reader_core.imports import (
    ImportJobCreationResult,
    ImportJobInputValidationError,
    ImportJobItemTarget,
)
from card_reader_core.repositories.content_versions import (
    create_next_content_version,
    normalize_description,
    parse_base_version,
)
from card_reader_core.repositories.import_jobs import (
    cancel_import_job,
    create_import_job,
    create_import_job_with_files,
    fetch_job_by_creation_key,
    prepare_import_job_inputs,
)
from card_reader_core.services.classification_rules import ClassificationRuleService
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
        accepted_creation_fingerprints: Sequence[str] = (),
        card_pool: CardPool,
        card_role_mode: CardClassificationMode = "automatic",
        card_role_override: Sequence[CardRole] = (),
        card_faction_mode: CardClassificationMode = "automatic",
        card_faction_override: Sequence[CardFaction] = (),
        card_mana_family_mode: CardClassificationMode = "automatic",
        card_mana_family_override: Sequence[ManaFamily] = (),
    ) -> ImportJobCreationResult:
        accepted_fingerprints = tuple(
            dict.fromkeys((creation_fingerprint, *accepted_creation_fingerprints))
        )
        existing = self.get_job_by_creation_key(creation_key=creation_key)
        if existing is not None:
            return ImportJobCreationResult(
                job=self._matching_replay(existing, accepted_fingerprints),
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
            card_mana_family_mode=card_mana_family_mode,
            card_mana_family_override=card_mana_family_override,
        )

        try:
            with transaction.atomic():
                rule_snapshot = self._build_rule_snapshot(
                    card_pool=card_pool,
                    card_role_mode=card_role_mode,
                    card_faction_mode=card_faction_mode,
                    card_mana_family_mode=card_mana_family_mode,
                )
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
                    card_mana_family_mode=card_mana_family_mode,
                    card_mana_family_override=card_mana_family_override,
                    classification_rule_snapshot=rule_snapshot,
                )
        except ImportJobInputValidationError as exc:
            raise ImportCreationRejected(str(exc)) from exc
        except IntegrityError:
            existing = self.get_job_by_creation_key(creation_key=creation_key)
            if existing is None:
                raise
            return ImportJobCreationResult(
                job=self._matching_replay(existing, accepted_fingerprints),
                outcome="replayed",
            )
        return ImportJobCreationResult(job=job, outcome="created")

    def create_reparse_job_with_files(
        self,
        *,
        source_path: Path,
        template_id: str,
        files: list[Path],
        item_targets: Sequence[ImportJobItemTarget],
        card_pool: CardPool,
    ) -> ImportJob:
        with transaction.atomic():
            rule_snapshot = self._build_rule_snapshot(
                card_pool=card_pool,
                card_role_mode=ImportClassificationMode.automatic,
                card_faction_mode=ImportClassificationMode.automatic,
                card_mana_family_mode=ImportClassificationMode.automatic,
            )
            return create_import_job_with_files(
                source_path=source_path,
                template_id=template_id,
                options={"reparse_existing": True},
                files=files,
                item_targets=item_targets,
                card_pool=card_pool,
                classification_rule_snapshot=rule_snapshot,
            )

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
        card_mana_family_mode: CardClassificationMode,
        card_mana_family_override: Sequence[ManaFamily],
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
                card_mana_family_mode=card_mana_family_mode,
                card_mana_family_override=card_mana_family_override,
            )
        except ValueError as exc:
            raise ImportCreationRejected(str(exc)) from exc

    def get_job_by_creation_key(self, *, creation_key: str) -> ImportJob | None:
        return fetch_job_by_creation_key(creation_key)

    def _matching_replay(
        self,
        job: ImportJob,
        accepted_fingerprints: Sequence[str],
    ) -> ImportJob:
        if job.creation_fingerprint not in accepted_fingerprints:
            raise ImportCreationKeyConflict(
                "This creation key has already been used for a different import payload."
            )
        return job

    def cancel_job(self, *, job_id: str) -> ImportJob | None:
        return cancel_import_job(job_id)

    @staticmethod
    def _build_rule_snapshot(
        *,
        card_pool: CardPool,
        card_role_mode: str,
        card_faction_mode: str,
        card_mana_family_mode: str,
    ) -> dict[str, object]:
        return ClassificationRuleService().build_snapshot(
            card_pool=card_pool,
            include_roles=card_role_mode == ImportClassificationMode.automatic,
            include_factions=card_faction_mode == ImportClassificationMode.automatic,
            include_mana_families=(
                card_mana_family_mode == ImportClassificationMode.automatic
            ),
        )
