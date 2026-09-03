import card_reader_core.models.base
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0061_fire_faction")]

    operations = [
        migrations.CreateModel(
            name="CardBackFactionDefault",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(default=card_reader_core.models.base.now_utc),
                ),
                (
                    "updated_at",
                    models.DateTimeField(default=card_reader_core.models.base.now_utc),
                ),
                (
                    "faction",
                    models.CharField(
                        choices=[
                            ("order", "Order"),
                            ("blood", "Blood"),
                            ("dark", "Dark"),
                            ("metal", "Metal"),
                            ("fire", "Fire"),
                        ],
                        max_length=64,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "card_back",
                    models.ForeignKey(
                        db_column="card_back_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="faction_defaults",
                        to="card_reader_core.cardback",
                    ),
                ),
            ],
            options={"db_table": "card_back_faction_default"},
        ),
        # Reversing the CreateModel would discard configured faction defaults.
        # Keep production schema evolution forward-only and require a snapshot
        # when operators intentionally need to restore pre-migration state.
        migrations.RunPython(migrations.RunPython.noop),
    ]
