from __future__ import annotations

from typing import NamedTuple, cast

from card_reader_core.models import CardPool, ImportJob, ImportJobItem, ImportJobStatus


class ImportItemTargetState(NamedTuple):
    was_targeted: bool
    live_card_pool: CardPool | None


def list_import_jobs(*, active_only: bool = False) -> list[ImportJob]:
    jobs = ImportJob.objects.select_related("content_version", "template")
    if active_only:
        jobs = jobs.filter(
            status__in=[
                ImportJobStatus.queued,
                ImportJobStatus.running,
                ImportJobStatus.canceling,
            ]
        )
    return list(jobs.order_by("-created_at"))


def fetch_job(job_id: str) -> ImportJob | None:
    return ImportJob.objects.select_related("content_version", "template").filter(id=job_id).first()


def fetch_job_by_creation_key(creation_key: str) -> ImportJob | None:
    return (
        ImportJob.objects.select_related("content_version", "template")
        .filter(creation_key=creation_key)
        .first()
    )


def fetch_items_for_job(job_id: str) -> list[ImportJobItem]:
    return list(
        ImportJobItem.objects.filter(job_id=job_id)
        .select_related(
            "job__content_version",
            "job__template",
            "target_card",
            "target_card_version",
            "classification_review_item",
        )
        .order_by("created_at")
    )


def fetch_import_item_target_state(item_id: str) -> ImportItemTargetState | None:
    row = (
        ImportJobItem.objects.filter(id=item_id)
        .values_list(
            "target_card_pool_snapshot",
            "target_card_id",
            "target_card_version_id",
            "target_card__card_pool",
            "target_card_version__card__card_pool",
        )
        .first()
    )
    if row is None:
        return None
    (
        target_pool_snapshot,
        target_card_id,
        target_card_version_id,
        target_card_pool,
        target_version_card_pool,
    ) = row
    return ImportItemTargetState(
        was_targeted=(
            target_pool_snapshot is not None
            or target_card_id is not None
            or target_card_version_id is not None
        ),
        live_card_pool=cast(
            CardPool | None,
            target_card_pool or target_version_card_pool,
        ),
    )


def get_next_queued_job() -> ImportJob | None:
    return (
        ImportJob.objects.select_related("content_version", "template")
        .filter(status=ImportJobStatus.queued)
        .order_by("created_at")
        .first()
    )
