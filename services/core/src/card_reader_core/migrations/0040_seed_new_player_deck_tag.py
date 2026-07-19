from __future__ import annotations

from uuid import uuid4

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def seed_new_player_deck_tag(apps: Apps, _schema_editor: BaseDatabaseSchemaEditor) -> None:
    deck_tag = apps.get_model("card_reader_core", "DeckTag")
    deck_tag.objects.get_or_create(
        kind="type",
        key="new-player",
        defaults={"id": str(uuid4()), "label": "New Player"},
    )


def remove_new_player_deck_tag(apps: Apps, _schema_editor: BaseDatabaseSchemaEditor) -> None:
    deck_tag = apps.get_model("card_reader_core", "DeckTag")
    deck_tag.objects.filter(kind="type", key="new-player").delete()


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0039_deck_tag_resubmissions")]

    operations = [
        migrations.RunPython(seed_new_player_deck_tag, remove_new_player_deck_tag),
    ]
