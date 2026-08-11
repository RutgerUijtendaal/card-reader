from __future__ import annotations

from pathlib import Path
from typing import Sequence
from uuid import uuid4

from django.db import transaction

from card_reader_core.models import (
    DEFAULT_CARD_POOL,
    CARD_ROLES,
    LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION,
    ContentVersion,
    ImportCardRoleMode,
    ImportJob,
    ImportJobItem,
    ImportJobStatus,
    CardPool,
    CardRole,
    is_card_pool,
    normalize_card_roles,
)
from card_reader_core.repositories.templates import get_template_by_key
from card_reader_core.storage import relativize_storage_path

from .files import collect_supported_files
from .types import ImportJobItemTarget


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
    card_role_mode: str = ImportCardRoleMode.automatic,
    card_role_override: Sequence[CardRole] = (),
    inference_policy_version: int = LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION,
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
    card_role_mode: str = ImportCardRoleMode.automatic,
    card_role_override: Sequence[CardRole] = (),
    inference_policy_version: int = LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION,
) -> ImportJob:
    normalized_targets = list(item_targets) if item_targets is not None else [None] * len(files)
    if len(normalized_targets) != len(files):
        raise ValueError("item_targets length must match files length")
    if not is_card_pool(card_pool):
        raise ValueError(f"Unsupported card pool: {card_pool}")
    if card_role_mode not in {ImportCardRoleMode.automatic, ImportCardRoleMode.override}:
        raise ValueError("card_role_mode must be either 'automatic' or 'override'.")
    normalized_mode = str(card_role_mode)
    normalized_override = normalize_card_roles(card_role_override)
    if len(set(card_role_override)) != len(normalized_override):
        raise ValueError("card_role_override contains unsupported or duplicate roles.")
    if normalized_mode == ImportCardRoleMode.automatic and normalized_override:
        raise ValueError("Automatic role inference cannot include role overrides.")
    if inference_policy_version != LATEST_CARD_ROLE_INFERENCE_POLICY_VERSION:
        raise ValueError(f"Unsupported card-role inference policy version: {inference_policy_version}")
    normalized_policy_version = inference_policy_version
    template = get_template_by_key(key=template_id)
    if template is None:
        raise ValueError(f"Unknown template_id '{template_id}'")

    template_roles = normalize_card_roles(template.inferred_card_roles_json)
    if len(set(template.inferred_card_roles_json)) != len(template_roles):
        invalid = sorted(set(template.inferred_card_roles_json) - set(CARD_ROLES))
        raise ValueError(
            "template.inferred_card_roles contains unsupported or duplicate roles"
            + (f": {', '.join(invalid)}" if invalid else ".")
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
            template=template,
            content_version=content_version,
            options_json=options,
            creation_key=resolved_creation_key,
            creation_fingerprint=resolved_fingerprint,
            card_pool=card_pool,
            card_role_mode=normalized_mode,
            card_role_override_json=list(normalized_override),
            template_role_snapshot_json=list(template_roles),
            card_role_inference_policy_version=normalized_policy_version,
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
                    status=ImportJobStatus.queued,
                )
                for image_file, target in zip(files, normalized_targets, strict=True)
            ]
        )
    return job
