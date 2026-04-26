from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

from .shared import resolve_seed_file

LOCAL_USERS_SEED_FILE = resolve_seed_file("seed-users.local.json")


@dataclass(frozen=True)
class SeedUser:
    username: str
    password: str
    is_staff: bool | None
    is_superuser: bool | None


@dataclass(frozen=True)
class UserSeedResult:
    created: int
    existing: int


def seed_users_from_config() -> UserSeedResult | None:
    seed_path = resolve_user_seed_file()
    if seed_path is None:
        return None
    return seed_users(seed_path)


def resolve_user_seed_file() -> Path | None:
    return LOCAL_USERS_SEED_FILE if LOCAL_USERS_SEED_FILE.exists() else None


def seed_users(seed_path: Path) -> UserSeedResult:
    if not seed_path.exists():
        raise CommandError(f"Seed users file does not exist: {seed_path}")
    if not seed_path.is_file():
        raise CommandError(f"Seed users path is not a file: {seed_path}")

    seed_entries = load_seed_users(seed_path)
    if not seed_entries:
        return UserSeedResult(created=0, existing=0)

    user_model = get_user_model()
    created_count = 0
    existing_count = 0
    for seed_user in seed_entries:
        user, created = user_model.objects.get_or_create(username=seed_user.username)
        changed_fields: list[str] = []

        if created:
            user.set_password(seed_user.password)
            changed_fields.append("password")
            created_count += 1
        else:
            existing_count += 1

        if seed_user.is_staff is not None and user.is_staff != seed_user.is_staff:
            user.is_staff = seed_user.is_staff
            changed_fields.append("is_staff")
        if seed_user.is_superuser is not None and user.is_superuser != seed_user.is_superuser:
            user.is_superuser = seed_user.is_superuser
            changed_fields.append("is_superuser")
        if changed_fields:
            user.save(update_fields=changed_fields)

    return UserSeedResult(created=created_count, existing=existing_count)


def load_seed_users(path: Path) -> list[SeedUser]:
    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandError(f"Seed users file is not valid JSON: {path}") from exc

    users_payload = raw_payload.get("users") if isinstance(raw_payload, dict) else None
    if not isinstance(users_payload, list):
        raise CommandError("Seed users JSON must contain a 'users' array.")

    return [_parse_seed_user(row, index=index) for index, row in enumerate(users_payload)]


def _parse_seed_user(raw_user: Any, *, index: int) -> SeedUser:
    if not isinstance(raw_user, dict):
        raise CommandError(f"Seed user at index {index} must be an object.")

    username = _required_string(raw_user, "username", index=index)
    password = _required_string(raw_user, "password", index=index)
    is_staff = _optional_bool(raw_user, "is_staff", index=index)
    is_superuser = _optional_bool(raw_user, "is_superuser", index=index)
    return SeedUser(
        username=username,
        password=password,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def _required_string(raw_user: dict[str, Any], key: str, *, index: int) -> str:
    value = raw_user.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CommandError(f"Seed user at index {index} must have a non-empty '{key}'.")
    return value.strip()


def _optional_bool(raw_user: dict[str, Any], key: str, *, index: int) -> bool | None:
    value = raw_user.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise CommandError(f"Seed user at index {index} has invalid '{key}'.")
    return value
