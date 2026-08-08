from __future__ import annotations

from datetime import datetime

from django.db.models import Count, F, Q

from card_reader_core.models import (
    DeveloperDataBuild,
    ImportJob,
    TtsCardSheet,
)
from card_reader_core.repositories.tts_card_sheets import (
    TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT,
)


def import_job_status_counts() -> dict[str, int]:
    return {
        str(row["status"]): int(row["count"])
        for row in ImportJob.objects.values("status").annotate(count=Count("id"))
    }


def list_import_jobs_for_operations(*, limit: int) -> list[ImportJob]:
    return list(
        ImportJob.objects.select_related("content_version", "template")
        .order_by("-updated_at")[:limit]
    )


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
    stale_before = now - TTS_CARD_SHEET_RENDER_CLAIM_TIMEOUT
    actively_claimed = Q(render_claimed_at__gte=stale_before)
    claimable = Q(render_claimed_at__isnull=True) | Q(render_claimed_at__lt=stale_before)
    no_failures = Q(render_failure_count=0)
    result = TtsCardSheet.objects.aggregate(
        completed=Count("id", filter=Q(desired_revision__lte=F("rendered_revision"))),
        running=Count("id", filter=pending & actively_claimed),
        retrying=Count("id", filter=pending & claimable & Q(render_failure_count__gt=0)),
        scheduled=Count(
            "id",
            filter=pending & claimable & no_failures & Q(render_not_before__gt=now),
        ),
        queued=Count(
            "id",
            filter=(
                pending
                & claimable
                & no_failures
                & (Q(render_not_before__isnull=True) | Q(render_not_before__lte=now))
            ),
        ),
    )
    return {key: int(value or 0) for key, value in result.items()}
