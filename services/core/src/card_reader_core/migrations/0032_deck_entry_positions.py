from __future__ import annotations

from typing import Any

from django.db import migrations, models


def backfill_entry_positions(apps: Any, schema_editor: Any) -> None:
    deck_entry_model = apps.get_model("card_reader_core", "DeckEntry")
    sideboard_entry_model = apps.get_model("card_reader_core", "DeckSideboardEntry")

    current_deck_id = None
    position = 0
    for entry in deck_entry_model.objects.order_by("deck_id", "card__label", "created_at", "id"):
        if entry.deck_id != current_deck_id:
            current_deck_id = entry.deck_id
            position = 1
        else:
            position += 1
        entry.position = position
        entry.save(update_fields=["position"])

    current_sideboard_id = None
    position = 0
    for entry in sideboard_entry_model.objects.order_by(
        "sideboard_id",
        "card__label",
        "created_at",
        "id",
    ):
        if entry.sideboard_id != current_sideboard_id:
            current_sideboard_id = entry.sideboard_id
            position = 1
        else:
            position += 1
        entry.position = position
        entry.save(update_fields=["position"])


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0031_user_notifications")]

    operations = [
        migrations.AddField(
            model_name="deckentry",
            name="position",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="decksideboardentry",
            name="position",
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(backfill_entry_positions, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="deckentry",
            index=models.Index(fields=["deck", "position"], name="ix_deck_entry_deck_pos"),
        ),
        migrations.AddIndex(
            model_name="decksideboardentry",
            index=models.Index(fields=["sideboard", "position"], name="ix_deck_side_entry_pos"),
        ),
    ]
