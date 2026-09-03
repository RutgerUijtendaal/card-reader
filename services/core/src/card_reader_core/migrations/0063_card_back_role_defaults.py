import card_reader_core.models.base
import django.db.models.deletion
from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.exceptions import IrreversibleError


def require_empty_role_defaults_for_rollback(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    CardBackRoleDefault = apps.get_model(
        "card_reader_core",
        "CardBackRoleDefault",
    )
    if CardBackRoleDefault.objects.exists():
        raise IrreversibleError(
            "Cannot reverse 0063_card_back_role_defaults while role-default "
            "assignments exist. Restore a pre-migration snapshot or remove the "
            "assignments before retrying."
        )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0062_card_back_faction_defaults")]

    operations = [
        migrations.CreateModel(
            name="CardBackRoleDefault",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("hero", "Hero"),
                            ("boss", "Boss"),
                            ("location", "Location"),
                            ("boon", "Boon"),
                            ("event", "Event"),
                            ("shop_item", "Shop Item"),
                            ("directive", "Directive"),
                            ("reminder", "Reminder"),
                            ("mana", "Mana"),
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
                        related_name="role_defaults",
                        to="card_reader_core.cardback",
                    ),
                ),
            ],
            options={"db_table": "card_back_role_default"},
        ),
        migrations.RunPython(
            migrations.RunPython.noop,
            require_empty_role_defaults_for_rollback,
        ),
    ]
