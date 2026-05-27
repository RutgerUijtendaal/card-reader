from typing import Any

from django.db import migrations, models


def migrate_deck_visibility(apps: Any, schema_editor: Any) -> None:
    deck_model = apps.get_model("card_reader_core", "Deck")
    deck_model.objects.filter(is_public=True).update(visibility="public")
    deck_model.objects.filter(is_public=False).update(visibility="private")


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0023_deck_sideboard_unique_cards")]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="visibility",
            field=models.CharField(
                choices=[("private", "Private"), ("unlisted", "Unlisted"), ("public", "Public")],
                db_index=True,
                default="private",
                max_length=16,
            ),
        ),
        migrations.RunPython(migrate_deck_visibility, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="deck",
            name="is_public",
        ),
    ]
