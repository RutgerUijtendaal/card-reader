from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


EVENT_TYPE = "deck.card_version_changed"
BATCH_SIZE = 500


def _backfill_batch(
    user_notification: Any,
    card_version: Any,
    notifications: Iterable[Any],
) -> None:
    batch = list(notifications)
    version_ids = {
        metadata.get("card_version_id")
        for notification in batch
        if isinstance((metadata := notification.metadata_json), dict)
        and not metadata.get("previous_card_version_id")
        and isinstance(metadata.get("card_version_id"), str)
    }
    versions = {
        str(version["id"]): version
        for version in card_version.objects.filter(id__in=version_ids).values(
            "id",
            "card_id",
            "previous_version_id",
        )
    }

    updates = []
    for notification in batch:
        metadata = notification.metadata_json
        if not isinstance(metadata, dict) or metadata.get("previous_card_version_id"):
            continue

        version_id = metadata.get("card_version_id")
        card_id = metadata.get("card_id")
        if not isinstance(version_id, str) or not isinstance(card_id, str):
            continue

        version = versions.get(version_id)
        if version is None or str(version["card_id"]) != card_id:
            continue

        previous_version_id = version["previous_version_id"]
        if previous_version_id is None:
            continue

        notification.metadata_json = {
            **metadata,
            "previous_card_version_id": str(previous_version_id),
        }
        updates.append(notification)

    if updates:
        user_notification.objects.bulk_update(
            updates,
            ["metadata_json"],
            batch_size=BATCH_SIZE,
        )


def backfill_notification_previous_versions(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    user_notification = apps.get_model("card_reader_core", "UserNotification")
    card_version = apps.get_model("card_reader_core", "CardVersion")
    notifications = user_notification.objects.filter(event_type=EVENT_TYPE).only(
        "id",
        "metadata_json",
    )

    batch = []
    for notification in notifications.iterator(chunk_size=BATCH_SIZE):
        batch.append(notification)
        if len(batch) == BATCH_SIZE:
            _backfill_batch(user_notification, card_version, batch)
            batch = []
    if batch:
        _backfill_batch(user_notification, card_version, batch)


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0043_notification_event_names")]

    operations = [
        migrations.RunPython(
            backfill_notification_previous_versions,
            migrations.RunPython.noop,
        ),
    ]
