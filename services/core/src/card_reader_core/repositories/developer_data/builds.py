from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from card_reader_core.models import DeveloperDataBuild, DeveloperDataBuildStatus
from card_reader_core.operations.developer_data.schema import PublishedBundle


class DeveloperDataBuildAlreadyActiveError(RuntimeError):
    pass


def create_build(*, requested_by: Any, bundle_version: str) -> DeveloperDataBuild:
    try:
        with transaction.atomic():
            return DeveloperDataBuild.objects.create(
                requested_by=requested_by,
                bundle_version=bundle_version,
            )
    except IntegrityError as exc:
        if DeveloperDataBuild.objects.filter(is_active_build=True).exists():
            raise DeveloperDataBuildAlreadyActiveError(
                "A developer-data build is already queued or running."
            ) from exc
        raise


def list_recent_builds(*, limit: int = 20) -> list[DeveloperDataBuild]:
    return list(DeveloperDataBuild.objects.select_related("requested_by").order_by("-created_at")[:limit])


def claim_next_build() -> DeveloperDataBuild | None:
    while True:
        candidate_id = (
            DeveloperDataBuild.objects.filter(status=DeveloperDataBuildStatus.queued)
            .order_by("created_at")
            .values_list("id", flat=True)
            .first()
        )
        if candidate_id is None:
            return None
        now = timezone.now()
        updated = DeveloperDataBuild.objects.filter(
            id=candidate_id,
            status=DeveloperDataBuildStatus.queued,
        ).update(
            status=DeveloperDataBuildStatus.running,
            started_at=now,
            updated_at=now,
            error_message="",
        )
        if updated:
            return DeveloperDataBuild.objects.select_related("requested_by").get(id=candidate_id)


def mark_build_succeeded(
    *,
    build_id: str,
    artifact: PublishedBundle,
) -> DeveloperDataBuild:
    now = timezone.now()
    DeveloperDataBuild.objects.filter(
        id=build_id,
        status=DeveloperDataBuildStatus.running,
    ).update(
        status=DeveloperDataBuildStatus.succeeded,
        is_active_build=False,
        finished_at=now,
        updated_at=now,
        format_version=artifact.format_version,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
        error_message="",
    )
    return DeveloperDataBuild.objects.select_related("requested_by").get(id=build_id)


def mark_build_failed(*, build_id: str, error_message: str) -> DeveloperDataBuild:
    now = timezone.now()
    DeveloperDataBuild.objects.filter(
        id=build_id,
        status=DeveloperDataBuildStatus.running,
    ).update(
        status=DeveloperDataBuildStatus.failed,
        is_active_build=False,
        finished_at=now,
        updated_at=now,
        error_message=error_message[:2000],
    )
    return DeveloperDataBuild.objects.select_related("requested_by").get(id=build_id)


def requeue_interrupted_builds() -> int:
    now = timezone.now()
    stale_before = now - timedelta(minutes=30)
    return DeveloperDataBuild.objects.filter(
        status=DeveloperDataBuildStatus.running,
        updated_at__lt=stale_before,
    ).update(
        status=DeveloperDataBuildStatus.queued,
        started_at=None,
        updated_at=now,
        error_message="Recovered after the developer-data worker restarted.",
    )
