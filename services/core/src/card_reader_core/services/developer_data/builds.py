from __future__ import annotations

from datetime import datetime
import secrets

from django.utils import timezone

from card_reader_core.models import DeveloperDataBuild
from card_reader_core.repositories.developer_data import (
    DeveloperDataBuildAlreadyActiveError,
    create_build,
    list_recent_builds,
)


def queue_developer_data_build(*, requested_by: object) -> DeveloperDataBuild:
    return create_build(
        requested_by=requested_by,
        bundle_version=_new_bundle_version(timezone.now()),
    )


def recent_developer_data_builds(*, limit: int = 20) -> list[DeveloperDataBuild]:
    return list_recent_builds(limit=limit)


def _new_bundle_version(now: datetime) -> str:
    return f"dev-{now:%Y.%m.%d-%H%M%S}-{secrets.token_hex(3)}"


__all__ = [
    "DeveloperDataBuildAlreadyActiveError",
    "queue_developer_data_build",
    "recent_developer_data_builds",
]
