from __future__ import annotations

from card_reader_core.models import Card, CardVersion, now_utc


def merge_card_versions(target_id: str, source_ids: list[str]) -> None:
    target = Card.objects.select_related("latest_version").get(id=target_id)
    target_latest_id = target.latest_version.id if target.latest_version is not None else None
    source_versions = list(CardVersion.objects.filter(card_id__in=source_ids).select_for_update())
    temp_start = 1_000_000
    for offset, version in enumerate(source_versions):
        setattr(version, "card_id", target_id)
        version.version_number = temp_start + offset
        version.is_latest = False
        version.updated_at = now_utc()
        version.save(update_fields=["card", "version_number", "is_latest", "updated_at"])

    versions = list(CardVersion.objects.filter(card_id=target_id).select_related("card").order_by("created_at", "version_number", "id"))
    for offset, version in enumerate(versions, start=1):
        version.version_number = temp_start + 10_000 + offset
        version.updated_at = now_utc()
        version.save(update_fields=["version_number", "updated_at"])

    target_latest = next((version for version in versions if version.id == target_latest_id), None)
    ordered_versions = [version for version in versions if version.id != target_latest_id]
    if target_latest is not None:
        ordered_versions.append(target_latest)
    latest_version = ordered_versions[-1] if ordered_versions else None
    previous_id: str | None = None
    for index, version in enumerate(ordered_versions, start=1):
        version.version_number = index
        setattr(version, "previous_version_id", previous_id)
        version.is_latest = latest_version is not None and version.id == latest_version.id
        version.updated_at = now_utc()
        version.save(update_fields=["version_number", "previous_version", "is_latest", "updated_at"])
        previous_id = version.id

    target.latest_version = latest_version
    target.updated_at = now_utc()
    if latest_version is not None:
        target.label = latest_version.name or target.label
    target.save(update_fields=["latest_version", "label", "updated_at"])
