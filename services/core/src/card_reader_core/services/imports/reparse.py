from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from django.db import transaction

from card_reader_core.config.settings import settings
from card_reader_core.imports import GroupedReparseSource, GroupedReparseSummary, ImportJobItemTarget
from card_reader_core.models import (
    CardFaction,
    CardPool,
    CardRole,
    normalize_card_factions,
    normalize_card_roles,
)
from card_reader_core.metadata import normalize_mana_family_keys
from .service import ImportService


def queue_grouped_reparse_jobs(
    *,
    sources: Sequence[GroupedReparseSource],
    source_name_prefix: str,
    source_root: str = "maintenance",
    target_template_id: str | None = None,
) -> GroupedReparseSummary:
    grouped: dict[
        tuple[str, CardPool, tuple[CardRole, ...], tuple[CardFaction, ...]],
        list[GroupedReparseSource],
    ] = defaultdict(list)
    for source in sources:
        template_id = target_template_id or source.template_id
        roles = normalize_card_roles(source.card_roles)
        factions = normalize_card_factions(source.card_factions)
        grouped[(template_id, source.card_pool, roles, factions)].append(source)

    with transaction.atomic():
        for (template_id, card_pool, _roles, _factions), group in sorted(grouped.items()):
            ImportService().create_reparse_job_with_files(
                source_path=(
                    settings.storage_root_dir
                    / source_root
                    / f"{source_name_prefix}-{template_id}"
                ),
                template_id=template_id,
                files=[source.image_path for source in group],
                item_targets=[
                    ImportJobItemTarget(
                        card_id=source.card_id,
                        card_version_id=source.card_version_id,
                        card_pool=source.card_pool,
                        card_roles=normalize_card_roles(source.card_roles),
                        card_factions=normalize_card_factions(source.card_factions),
                        card_mana_families=normalize_mana_family_keys(
                            tuple(source.card_mana_families)
                        ),
                    )
                    for source in group
                ],
                card_pool=card_pool,
            )

    return GroupedReparseSummary(job_count=len(grouped), item_count=len(sources))
