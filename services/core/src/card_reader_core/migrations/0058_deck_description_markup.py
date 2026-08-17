from typing import Any

from django.db import migrations, models


def backfill_deck_markup(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    deck_model = apps.get_model("card_reader_core", "Deck")
    for deck in deck_model.objects.all().iterator():
        deck.description_markup = deck.description
        deck.long_description_markup = deck.long_description
        deck.save(update_fields=["description_markup", "long_description_markup"])


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0057_card_classification_review_item")]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="description_markup",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="deck",
            name="long_description_markup",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.RunPython(backfill_deck_markup, migrations.RunPython.noop),
    ]
