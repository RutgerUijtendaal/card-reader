from __future__ import annotations

from pathlib import Path
from typing import Sequence
from uuid import uuid4

from django.db import transaction

from card_reader_core.imports import (
    ImportJobInputValidationError,
    ImportJobItemTarget,
    PreparedImportJobInputs,
)
from card_reader_core.models import (
    DEFAULT_CARD_POOL,
    CARD_FACTIONS,
    CARD_ROLES,
    LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION,
    ContentVersion,
    ImportClassificationMode,
    ImportJob,
    ImportJobItem,
    ImportJobStatus,
    CardFaction,
    CardPool,
    CardRole,
    is_card_pool,
    normalize_card_factions,
    normalize_card_roles,
)
from card_reader_core.repositories.templates import get_template_by_key
from card_reader_core.storage import relativize_storage_path

from .files import collect_supported_files


def create_import_job(
    *,
    source_path: Path,
    template_id: str,
    options: dict[str, object],
    content_version: ContentVersion | None = None,
    item_targets: Sequence[ImportJobItemTarget | None] | None = None,
    creation_key: str | None = None,
    creation_fingerprint: str | None = None,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    card_role_mode: str = ImportClassificationMode.automatic,
    card_role_override: Sequence[CardRole] = (),
    card_faction_mode: str = ImportClassificationMode.automatic,
    card_faction_override: Sequence[CardFaction] = (),
    inference_policy_version: int = LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION,
) -> ImportJob:
    files = collect_supported_files(source_path)
    return create_import_job_with_files(
        source_path=source_path,
        template_id=template_id,
        options=options,
        content_version=content_version,
        files=files,
        item_targets=item_targets,
        creation_key=creation_key,
        creation_fingerprint=creation_fingerprint,
        card_pool=card_pool,
        card_role_mode=card_role_mode,
        card_role_override=card_role_override,
        card_faction_mode=card_faction_mode,
        card_faction_override=card_faction_override,
        inference_policy_version=inference_policy_version,
    )


def create_import_job_with_files(
    *,
    source_path: Path,
    template_id: str,
    options: dict[str, object],
    files: list[Path],
    content_version: ContentVersion | None = None,
    item_targets: Sequence[ImportJobItemTarget | None] | None = None,
    creation_key: str | None = None,
    creation_fingerprint: str | None = None,
    card_pool: CardPool = DEFAULT_CARD_POOL,
    card_role_mode: str = ImportClassificationMode.automatic,
    card_role_override: Sequence[CardRole] = (),
    card_faction_mode: str = ImportClassificationMode.automatic,
    card_faction_override: Sequence[CardFaction] = (),
    inference_policy_version: int = LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION,
) -> ImportJob:
    normalized_targets = list(item_targets) if item_targets is not None else [None] * len(files)
    if len(normalized_targets) != len(files):
        raise ValueError("item_targets length must match files length")
    prepared = prepare_import_job_inputs(
        template_id=template_id,
        card_pool=card_pool,
        card_role_mode=card_role_mode,
        card_role_override=card_role_override,
        card_faction_mode=card_faction_mode,
        card_faction_override=card_faction_override,
        inference_policy_version=inference_policy_version,
    )
    resolved_creation_key = creation_key or str(uuid4())
    resolved_fingerprint = creation_fingerprint or f"internal:{resolved_creation_key}"

    with transaction.atomic():
        job = ImportJob.objects.create(
            source_path=relativize_storage_path(
                source_path,
                default_root="uploads",
                preserve_unmatched_absolute=True,
            ),
            template=prepared.template,
            content_version=content_version,
            options_json=options,
            creation_key=resolved_creation_key,
            creation_fingerprint=resolved_fingerprint,
            card_pool=card_pool,
            card_role_mode=prepared.card_role_mode,
            card_role_override_json=list(prepared.card_role_override),
            template_role_snapshot_json=list(prepared.template_roles),
            card_faction_mode=prepared.card_faction_mode,
            card_faction_override_json=list(prepared.card_faction_override),
            template_faction_snapshot_json=list(prepared.template_factions),
            classification_inference_policy_version=prepared.inference_policy_version,
            total_items=len(files),
            processed_items=0,
        )
        ImportJobItem.objects.bulk_create(
            [
                ImportJobItem(
                    job=job,
                    source_file=relativize_storage_path(
                        image_file,
                        default_root="uploads",
                        preserve_unmatched_absolute=True,
                    ),
                    target_card_id=target.card_id if target is not None else None,
                    target_card_version_id=target.card_version_id if target is not None else None,
                    target_card_pool_snapshot=target.card_pool if target is not None else None,
                    target_card_roles_snapshot_json=(list(target.card_roles) if target is not None else []),
                    target_card_factions_snapshot_json=(
                        list(target.card_factions) if target is not None else []
                    ),
                    status=ImportJobStatus.queued,
                )
                for image_file, target in zip(files, normalized_targets, strict=True)
            ]
        )
    return job


def prepare_import_job_inputs(
    *,
    template_id: str,
    card_pool: CardPool,
    card_role_mode: str,
    card_role_override: Sequence[CardRole],
    card_faction_mode: str,
    card_faction_override: Sequence[CardFaction],
    inference_policy_version: int,
) -> PreparedImportJobInputs:
    if not is_card_pool(card_pool):
        raise ImportJobInputValidationError(f"Unsupported card pool: {card_pool}")
    if card_role_mode not in {
        ImportClassificationMode.automatic,
        ImportClassificationMode.override,
    }:
        raise ImportJobInputValidationError(
            "card_role_mode must be either 'automatic' or 'override'."
        )
    normalized_mode = str(card_role_mode)
    normalized_override = normalize_card_roles(card_role_override)
    if len(set(card_role_override)) != len(normalized_override):
        raise ImportJobInputValidationError(
            "card_role_override contains unsupported or duplicate roles."
        )
    if normalized_mode == ImportClassificationMode.automatic and normalized_override:
        raise ImportJobInputValidationError(
            "Automatic role inference cannot include role overrides."
        )
    if card_faction_mode not in {
        ImportClassificationMode.automatic,
        ImportClassificationMode.override,
    }:
        raise ImportJobInputValidationError(
            "card_faction_mode must be either 'automatic' or 'override'."
        )
    normalized_faction_mode = str(card_faction_mode)
    normalized_faction_override = normalize_card_factions(card_faction_override)
    if len(set(card_faction_override)) != len(normalized_faction_override):
        raise ImportJobInputValidationError(
            "card_faction_override contains unsupported or duplicate factions."
        )
    if (
        normalized_faction_mode == ImportClassificationMode.automatic
        and normalized_faction_override
    ):
        raise ImportJobInputValidationError(
            "Automatic faction inference cannot include faction overrides."
        )
    if inference_policy_version != LATEST_CLASSIFICATION_INFERENCE_POLICY_VERSION:
        raise ImportJobInputValidationError(
            f"Unsupported card-classification inference policy version: {inference_policy_version}"
        )
    template = get_template_by_key(key=template_id)
    if template is None:
        raise ImportJobInputValidationError(f"Unknown template_id '{template_id}'")

    template_roles = normalize_card_roles(template.inferred_card_roles_json)
    if len(set(template.inferred_card_roles_json)) != len(template_roles):
        invalid = sorted(set(template.inferred_card_roles_json) - set(CARD_ROLES))
        raise ImportJobInputValidationError(
            "template.inferred_card_roles contains unsupported or duplicate roles"
            + (f": {', '.join(invalid)}" if invalid else ".")
        )
    template_factions = normalize_card_factions(template.inferred_card_factions_json)
    if len(set(template.inferred_card_factions_json)) != len(template_factions):
        invalid_factions = sorted(
            set(template.inferred_card_factions_json) - set(CARD_FACTIONS)
        )
        raise ImportJobInputValidationError(
            "template.inferred_card_factions contains unsupported or duplicate factions"
            + (f": {', '.join(invalid_factions)}" if invalid_factions else ".")
        )
    return PreparedImportJobInputs(
        template=template,
        card_role_mode=normalized_mode,
        card_role_override=normalized_override,
        template_roles=template_roles,
        card_faction_mode=normalized_faction_mode,
        card_faction_override=normalized_faction_override,
        template_factions=template_factions,
        inference_policy_version=inference_policy_version,
    )
