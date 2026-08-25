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
from card_reader_core.metadata import ManaFamily, normalize_mana_family_keys
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
    card_mana_family_mode: str = ImportClassificationMode.automatic,
    card_mana_family_override: Sequence[ManaFamily] = (),
    classification_rule_snapshot: dict[str, object],
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
        card_mana_family_mode=card_mana_family_mode,
        card_mana_family_override=card_mana_family_override,
        classification_rule_snapshot=classification_rule_snapshot,
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
    card_mana_family_mode: str = ImportClassificationMode.automatic,
    card_mana_family_override: Sequence[ManaFamily] = (),
    classification_rule_snapshot: dict[str, object],
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
        card_mana_family_mode=card_mana_family_mode,
        card_mana_family_override=card_mana_family_override,
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
            card_faction_mode=prepared.card_faction_mode,
            card_faction_override_json=list(prepared.card_faction_override),
            card_mana_family_mode=prepared.card_mana_family_mode,
            card_mana_family_override_json=list(prepared.card_mana_family_override),
            classification_rule_snapshot_json=classification_rule_snapshot,
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
                    target_card_roles_snapshot_json=(
                        list(target.card_roles) if target is not None else []
                    ),
                    target_card_factions_snapshot_json=(
                        list(target.card_factions) if target is not None else []
                    ),
                    target_card_mana_families_snapshot_json=(
                        list(target.card_mana_families) if target is not None else []
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
    card_mana_family_mode: str,
    card_mana_family_override: Sequence[ManaFamily],
) -> PreparedImportJobInputs:
    if not is_card_pool(card_pool):
        raise ImportJobInputValidationError(f"Unsupported card pool: {card_pool}")
    normalized_mode = _validated_classification_mode(card_role_mode, field="card_role_mode")
    normalized_override = normalize_card_roles(card_role_override)
    _validate_classification_override(
        raw_values=card_role_override,
        normalized_values=normalized_override,
        mode=normalized_mode,
        duplicate_error="card_role_override contains unsupported or duplicate roles.",
        automatic_error="Automatic role inference cannot include role overrides.",
    )
    normalized_faction_mode = _validated_classification_mode(
        card_faction_mode,
        field="card_faction_mode",
    )
    normalized_faction_override = normalize_card_factions(card_faction_override)
    _validate_classification_override(
        raw_values=card_faction_override,
        normalized_values=normalized_faction_override,
        mode=normalized_faction_mode,
        duplicate_error="card_faction_override contains unsupported or duplicate factions.",
        automatic_error="Automatic faction inference cannot include faction overrides.",
    )
    normalized_mana_family_mode = _validated_classification_mode(
        card_mana_family_mode,
        field="card_mana_family_mode",
    )
    normalized_mana_family_override = normalize_mana_family_keys(
        tuple(card_mana_family_override)
    )
    _validate_classification_override(
        raw_values=card_mana_family_override,
        normalized_values=normalized_mana_family_override,
        mode=normalized_mana_family_mode,
        duplicate_error=(
            "card_mana_family_override contains unsupported or duplicate families."
        ),
        automatic_error=(
            "Automatic mana family inference cannot include mana family overrides."
        ),
    )
    template = get_template_by_key(key=template_id)
    if template is None:
        raise ImportJobInputValidationError(f"Unknown template_id '{template_id}'")

    return PreparedImportJobInputs(
        template=template,
        card_role_mode=normalized_mode,
        card_role_override=normalized_override,
        card_faction_mode=normalized_faction_mode,
        card_faction_override=normalized_faction_override,
        card_mana_family_mode=normalized_mana_family_mode,
        card_mana_family_override=normalized_mana_family_override,
    )


def _validated_classification_mode(mode: str, *, field: str) -> str:
    allowed_modes = {
        ImportClassificationMode.automatic,
        ImportClassificationMode.override,
    }
    if mode not in allowed_modes:
        raise ImportJobInputValidationError(
            f"{field} must be either 'automatic' or 'override'."
        )
    return str(mode)


def _validate_classification_override(
    *,
    raw_values: Sequence[object],
    normalized_values: Sequence[object],
    mode: str,
    duplicate_error: str,
    automatic_error: str,
) -> None:
    if len(set(raw_values)) != len(normalized_values):
        raise ImportJobInputValidationError(duplicate_error)
    if mode == ImportClassificationMode.automatic and normalized_values:
        raise ImportJobInputValidationError(automatic_error)
