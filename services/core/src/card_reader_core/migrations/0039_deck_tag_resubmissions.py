from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0038_deck_tags")]

    operations = [
        migrations.AddField(
            model_name="decktagsuggestion",
            name="rejected_resubmission_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="decktagsuggestiondeck",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddIndex(
            model_name="decktagsuggestiondeck",
            index=models.Index(
                fields=["suggestion", "is_active"],
                name="ix_deck_tag_sugg_active",
            ),
        ),
    ]
