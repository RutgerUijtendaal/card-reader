from __future__ import annotations

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


EVENT_TYPE_RENAMES = (
    ("parse_flag.reviewed", "parse_flag_item.reviewed"),
    ("deck.card_changed", "deck.card_version_changed"),
)


def _rename_event_types(apps: Apps, renames: tuple[tuple[str, str], ...]) -> None:
    user_notification = apps.get_model("card_reader_core", "UserNotification")
    for old_event_type, new_event_type in renames:
        user_notification.objects.filter(event_type=old_event_type).update(event_type=new_event_type)
        old_prefix = f"{old_event_type}:"
        for notification in user_notification.objects.filter(dedupe_key__startswith=old_prefix).iterator():
            notification.dedupe_key = f"{new_event_type}:{notification.dedupe_key[len(old_prefix):]}"
            notification.save(update_fields=["dedupe_key"])


def rename_notification_event_types(apps: Apps, _schema_editor: BaseDatabaseSchemaEditor) -> None:
    _rename_event_types(apps, EVENT_TYPE_RENAMES)


def restore_notification_event_types(apps: Apps, _schema_editor: BaseDatabaseSchemaEditor) -> None:
    _rename_event_types(apps, tuple((new, old) for old, new in EVENT_TYPE_RENAMES))


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0042_deck_difficulty")]

    operations = [
        migrations.RunPython(rename_notification_event_types, restore_notification_event_types),
    ]
