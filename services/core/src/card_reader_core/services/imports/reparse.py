from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from django.db import transaction

from card_reader_core.config.settings import settings
from card_reader_core.imports import GroupedReparseSource, GroupedReparseSummary, ImportJobItemTarget
from card_reader_core.models import CardPool, CardRole, normalize_card_roles
from card_reader_core.repositories.import_jobs import create_import_job_with_files


def queue_grouped_reparse_jobs(
    *,
    sources: Sequence[GroupedReparseSource],
    source_name_prefix: str,
    source_root: str = "maintenance",
    target_template_id: str | None = None,
) -> GroupedReparseSummary:
    grouped: dict[
        tuple[str, CardPool, tuple[CardRole, ...]],
        list[GroupedReparseSource],
    ] = defaultdict(list)
    for source in sources:
        template_id = target_template_id or source.template_id
        roles = normalize_card_roles(source.card_roles)
        grouped[(template_id, source.card_pool, roles)].append(source)

    with transaction.atomic():
        for (template_id, card_pool, _roles), group in sorted(grouped.items()):
            create_import_job_with_files(
                source_path=(
                    settings.storage_root_dir
                    / source_root
                    / f"{source_name_prefix}-{template_id}"
                ),
                template_id=template_id,
                options={"reparse_existing": True},
                files=[source.image_path for source in group],
                item_targets=[
                    ImportJobItemTarget(
                        card_id=source.card_id,
                        card_version_id=source.card_version_id,
                        card_pool=source.card_pool,
                        card_roles=normalize_card_roles(source.card_roles),
                    )
                    for source in group
                ],
                card_pool=card_pool,
            )

    return GroupedReparseSummary(job_count=len(grouped), item_count=len(sources))
