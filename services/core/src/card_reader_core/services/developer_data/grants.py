from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Any

from django.conf import settings as django_settings
from django.utils import timezone

from card_reader_core.models import DeveloperDataDownloadGrant
from card_reader_core.repositories.developer_data import (
    authorize_download_token,
    consume_download_code,
    create_download_grant,
    download_code_is_exchangeable,
    purge_expired_download_grants,
)
from card_reader_core.services.user_roles import DEVELOPER_ROLE_NAME, has_developer_role

CODE_LIFETIME_MINUTES = 10
TOKEN_LIFETIME_MINUTES = 30
GRANT_RETENTION_DAYS = 30
_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


@dataclass(frozen=True)
class DownloadCode:
    value: str
    expires_at: datetime


@dataclass(frozen=True)
class DownloadToken:
    value: str
    expires_at: datetime
    grant: DeveloperDataDownloadGrant


class DeveloperDataGrantService:
    def create_code(self, *, user: Any) -> DownloadCode:
        if not _can_download_developer_data(user):
            raise PermissionError("Developer-data access is required.")
        now = timezone.now()
        _purge_old_grants(now)
        compact = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(20))
        value = "-".join(compact[index : index + 5] for index in range(0, 20, 5))
        expires_at = now + timedelta(minutes=CODE_LIFETIME_MINUTES)
        create_download_grant(
            user=user,
            code_hash=_secret_hash(compact),
            expires_at=expires_at,
        )
        return DownloadCode(value=value, expires_at=expires_at)

    def exchange_code(self, *, code: str, bundle_version: str) -> DownloadToken | None:
        compact_code = _normalize_code(code)
        compact_version = bundle_version.strip()
        if len(compact_code) != 20 or not compact_version:
            return None
        _purge_old_grants(timezone.now())
        raw_token = secrets.token_urlsafe(32)
        token_expires_at = timezone.now() + timedelta(minutes=TOKEN_LIFETIME_MINUTES)
        grant = consume_download_code(
            code_hash=_secret_hash(compact_code),
            bundle_version=compact_version,
            token_hash=_secret_hash(raw_token),
            token_expires_at=token_expires_at,
            developer_role_name=DEVELOPER_ROLE_NAME,
        )
        if grant is None:
            return None
        return DownloadToken(value=raw_token, expires_at=token_expires_at, grant=grant)

    def can_exchange_code(self, *, code: str) -> bool:
        compact_code = _normalize_code(code)
        if len(compact_code) != 20:
            return False
        _purge_old_grants(timezone.now())
        return download_code_is_exchangeable(
            code_hash=_secret_hash(compact_code),
            developer_role_name=DEVELOPER_ROLE_NAME,
        )

    def authorize_token(
        self,
        *,
        token: str,
        bundle_version: str,
    ) -> DeveloperDataDownloadGrant | None:
        compact_token = token.strip()
        compact_version = bundle_version.strip()
        if not compact_token or not compact_version:
            return None
        _purge_old_grants(timezone.now())
        return authorize_download_token(
            token_hash=_secret_hash(compact_token),
            bundle_version=compact_version,
            developer_role_name=DEVELOPER_ROLE_NAME,
        )


def _normalize_code(code: str) -> str:
    return "".join(character for character in code.upper() if character.isalnum())


def _secret_hash(value: str) -> str:
    return hmac.new(
        key=str(django_settings.SECRET_KEY).encode("utf-8"),
        msg=value.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _can_download_developer_data(user: Any) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and (getattr(user, "is_staff", False) or has_developer_role(user))
    )


def _purge_old_grants(now: datetime) -> None:
    purge_expired_download_grants(before=now - timedelta(days=GRANT_RETENTION_DAYS))
