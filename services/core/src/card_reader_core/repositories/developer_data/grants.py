from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from card_reader_core.models import DeveloperDataDownloadGrant


def purge_expired_download_grants(*, before: datetime) -> int:
    deleted, _ = DeveloperDataDownloadGrant.objects.filter(created_at__lt=before).delete()
    return deleted


def download_code_is_exchangeable(*, code_hash: str, developer_role_name: str) -> bool:
    return DeveloperDataDownloadGrant.objects.filter(
        code_hash=code_hash,
        exchanged_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
        user__is_active=True,
    ).filter(
        Q(user__is_staff=True) | Q(user__groups__name=developer_role_name)
    ).exists()


@transaction.atomic
def create_download_grant(
    *,
    user: Any,
    code_hash: str,
    expires_at: datetime,
) -> DeveloperDataDownloadGrant:
    now = timezone.now()
    DeveloperDataDownloadGrant.objects.select_for_update().filter(
        user=user,
        exchanged_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now, updated_at=now)
    return DeveloperDataDownloadGrant.objects.create(
        user=user,
        code_hash=code_hash,
        expires_at=expires_at,
    )


@transaction.atomic
def consume_download_code(
    *,
    code_hash: str,
    bundle_version: str,
    token_hash: str,
    token_expires_at: datetime,
    developer_role_name: str,
) -> DeveloperDataDownloadGrant | None:
    now = timezone.now()
    grant = (
        DeveloperDataDownloadGrant.objects.select_for_update()
        .select_related("user")
        .filter(
            code_hash=code_hash,
            exchanged_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=now,
            user__is_active=True,
        )
        .filter(Q(user__is_staff=True) | Q(user__groups__name=developer_role_name))
        .first()
    )
    if grant is None:
        return None
    grant.bundle_version = bundle_version
    grant.token_hash = token_hash
    grant.exchanged_at = now
    grant.token_expires_at = token_expires_at
    grant.updated_at = now
    grant.save(
        update_fields=[
            "bundle_version",
            "token_hash",
            "exchanged_at",
            "token_expires_at",
            "updated_at",
        ]
    )
    return grant


def authorize_download_token(
    *,
    token_hash: str,
    bundle_version: str,
    developer_role_name: str,
) -> DeveloperDataDownloadGrant | None:
    now = timezone.now()
    grant = (
        DeveloperDataDownloadGrant.objects.select_related("user")
        .filter(
            token_hash=token_hash,
            bundle_version=bundle_version,
            token_expires_at__gt=now,
            revoked_at__isnull=True,
            user__is_active=True,
        )
        .filter(Q(user__is_staff=True) | Q(user__groups__name=developer_role_name))
        .first()
    )
    if grant is None:
        return None
    DeveloperDataDownloadGrant.objects.filter(id=grant.id).update(
        last_download_at=now,
        updated_at=now,
    )
    grant.last_download_at = now
    return grant
