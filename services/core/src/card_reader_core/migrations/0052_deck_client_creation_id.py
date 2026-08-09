from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0051_card_version_mana_family_sort_key")]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="client_creation_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="deck",
            constraint=models.UniqueConstraint(
                fields=("owner", "client_creation_id"),
                name="ux_deck_owner_creation_id",
            ),
        ),
    ]
