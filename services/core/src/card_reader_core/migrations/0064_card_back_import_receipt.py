import card_reader_core.models.base
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("card_reader_core", "0063_card_back_role_defaults"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CardBackImportReceipt",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                (
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("client_request_id", models.UUIDField()),
                ("hero_card_id", models.TextField(null=True)),
                ("error", models.TextField(default="")),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="card_back_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "card_back",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="import_receipts",
                        to="card_reader_core.cardback",
                    ),
                ),
            ],
            options={
                "db_table": "card_back_import_receipt",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("owner", "client_request_id"), name="ux_card_back_import_owner_key"
                    )
                ],
            },
        ),
    ]
