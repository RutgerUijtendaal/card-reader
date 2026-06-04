from __future__ import annotations

import re

from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count

from card_reader_core.models import ContentVersion

BASE_VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
VERSION_NUMBER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def create_next_content_version(*, base_version: str, description: str) -> ContentVersion:
    major, minor = parse_base_version(base_version)
    normalized_base = f"{major}.{minor}"
    normalized_description = normalize_description(description)

    with transaction.atomic():
        latest_patch = (
            ContentVersion.objects.select_for_update()
            .filter(major=major, minor=minor)
            .order_by("-patch")
            .values_list("patch", flat=True)
            .first()
        )
        patch = 0 if latest_patch is None else int(latest_patch) + 1
        return ContentVersion.objects.create(
            version_number=f"{normalized_base}.{patch}",
            base_version=normalized_base,
            major=major,
            minor=minor,
            patch=patch,
            description=normalized_description,
        )


def get_current_content_version() -> ContentVersion | None:
    return ContentVersion.objects.order_by("-major", "-minor", "-patch").first()


def list_content_versions() -> list[ContentVersion]:
    return list(
        ContentVersion.objects.annotate(card_count=Count("card_versions", distinct=True)).order_by(
            "-major",
            "-minor",
            "-patch",
        )
    )


def update_content_version(
    version_id: str,
    *,
    version_number: str | None = None,
    description: str | None = None,
) -> ContentVersion | None:
    version = ContentVersion.objects.filter(id=version_id).first()
    if version is None:
        return None

    update_fields: list[str] = []
    if version_number is not None:
        major, minor, patch = parse_version_number(version_number)
        version.major = major
        version.minor = minor
        version.patch = patch
        version.base_version = f"{major}.{minor}"
        version.version_number = f"{major}.{minor}.{patch}"
        update_fields.extend(["major", "minor", "patch", "base_version", "version_number"])
    if description is not None:
        version.description = normalize_description(description)
        update_fields.append("description")

    if not update_fields:
        return version

    try:
        version.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
    except IntegrityError as exc:
        raise ValueError("Version number already exists.") from exc
    return version


def parse_base_version(value: str) -> tuple[int, int]:
    normalized = value.strip()
    if not BASE_VERSION_PATTERN.fullmatch(normalized):
        raise ValueError("Version must use major.minor digits, for example 14.1.")
    major_text, minor_text = normalized.split(".", 1)
    return int(major_text), int(minor_text)


def parse_version_number(value: str) -> tuple[int, int, int]:
    normalized = value.strip()
    if not VERSION_NUMBER_PATTERN.fullmatch(normalized):
        raise ValueError("Version must use major.minor.patch digits, for example 14.1.0.")
    major_text, minor_text, patch_text = normalized.split(".", 2)
    return int(major_text), int(minor_text), int(patch_text)


def normalize_description(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Version description is required.")
    return normalized


__all__ = [
    "BASE_VERSION_PATTERN",
    "VERSION_NUMBER_PATTERN",
    "create_next_content_version",
    "get_current_content_version",
    "list_content_versions",
    "normalize_description",
    "parse_base_version",
    "parse_version_number",
    "update_content_version",
]
