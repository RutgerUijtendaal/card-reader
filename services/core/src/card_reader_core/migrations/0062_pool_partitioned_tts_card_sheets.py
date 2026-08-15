from __future__ import annotations

from typing import Any

from django.db import migrations, models


CARD_POOL_CHOICES = [("player", "Player"), ("evil", "Evil"), ("neutral", "Neutral")]


def guard_reverse_restricted_sheets(apps: Any, _schema_editor: Any) -> None:
    TtsCardSheet = apps.get_model("card_reader_core", "TtsCardSheet")
    TtsCardSheetSlot = apps.get_model("card_reader_core", "TtsCardSheetSlot")
    if TtsCardSheet.objects.exclude(card_pool="player").exists() or TtsCardSheetSlot.objects.exclude(
        card_pool="player"
    ).exists():
        raise RuntimeError(
            "TTS card-sheet migration 0062 cannot be reversed while Evil or Neutral sheet data "
            "exists. Remove those pool-partitioned sheets explicitly before rolling back."
        )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0061_admin_owned_classification_rules")]

    operations = [
        migrations.AddField(
            model_name="ttscardsheet",
            name="card_pool",
            field=models.CharField(
                choices=CARD_POOL_CHOICES,
                db_index=True,
                default="player",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="ttscardsheetslot",
            name="card_pool",
            field=models.CharField(
                choices=CARD_POOL_CHOICES,
                db_index=True,
                default="player",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="ttscardsheetslot",
            name="card_identity_id",
            field=models.TextField(db_index=True),
        ),
        migrations.AddConstraint(
            model_name="ttscardsheetslot",
            constraint=models.UniqueConstraint(
                fields=("card_pool", "card_identity_id"),
                name="ux_tts_sheet_slot_pool_identity",
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, guard_reverse_restricted_sheets),
    ]
