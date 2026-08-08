from __future__ import annotations

from datetime import datetime

from django.db.models import Count, F, Q

from card_reader_core.models import (
    DeveloperDataBuild,
    ImportJob,
    ImportJobStatus,
    TtsCardSheet,
)


def import_job_status_counts() -> dict[str, int]:
    return {
        str(row["status"]): int(row["count"])
        for row in ImportJob.objects.values("status").annotate(count=Count("id"))
    }


def list_import_jobs_for_operations(*, limit: int) -> list[ImportJob]:
    active_statuses = [
        ImportJobStatus.running,
        ImportJobStatus.canceling,
        ImportJobStatus.queued,
    ]
    active = list(
        ImportJob.objects.select_related("content_version", "template")
        .filter(status__in=active_statuses)
        .order_by("-updated_at")[:limit]
    )
    remaining = max(0, limit - len(active))
    if remaining == 0:
        return active
    recent = list(
        ImportJob.objects.select_related("content_version", "template")
        .exclude(id__in=[job.id for job in active])
        .order_by("-updated_at")[:remaining]
    )
    return [*active, *recent]


def list_recent_developer_data_builds(*, limit: int) -> list[DeveloperDataBuild]:
    return list(
        DeveloperDataBuild.objects.select_related("requested_by").order_by("-updated_at")[:limit]
    )


def developer_data_build_status_counts() -> dict[str, int]:
    return {
        str(row["status"]): int(row["count"])
        for row in DeveloperDataBuild.objects.values("status").annotate(count=Count("id"))
    }


def list_tts_card_sheets_for_operations(*, limit: int) -> list[TtsCardSheet]:
    pending = list(
        TtsCardSheet.objects.filter(desired_revision__gt=F("rendered_revision"))
        .order_by("-updated_at")[:limit]
    )
    remaining = max(0, limit - len(pending))
    if remaining == 0:
        return pending
    recent = list(
        TtsCardSheet.objects.exclude(id__in=[sheet.id for sheet in pending])
        .order_by("-updated_at")[:remaining]
    )
    return [*pending, *recent]


def tts_card_sheet_status_counts(*, now: datetime) -> dict[str, int]:
    pending = Q(desired_revision__gt=F("rendered_revision"))
    unclaimed = Q(render_claimed_at__isnull=True)
    no_failures = Q(render_failure_count=0)
    result = TtsCardSheet.objects.aggregate(
        completed=Count("id", filter=Q(desired_revision__lte=F("rendered_revision"))),
        running=Count("id", filter=pending & Q(render_claimed_at__isnull=False)),
        retrying=Count("id", filter=pending & unclaimed & Q(render_failure_count__gt=0)),
        scheduled=Count(
            "id",
            filter=pending & unclaimed & no_failures & Q(render_not_before__gt=now),
        ),
        queued=Count(
            "id",
            filter=(
                pending
                & unclaimed
                & no_failures
                & (Q(render_not_before__isnull=True) | Q(render_not_before__lte=now))
            ),
        ),
    )
    return {key: int(value or 0) for key, value in result.items()}
