from __future__ import annotations

import card_reader_core.models.base
from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [("card_reader_core", "0017_metadata_suggestions")]

    operations = [
        migrations.CreateModel(
            name="CardGroup",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("key", models.TextField(db_index=True, default="", unique=True)),
                ("name", models.TextField(default="")),
                (
                    "anchor_card",
                    models.ForeignKey(
                        db_column="anchor_card_id",
                        on_delete=models.PROTECT,
                        related_name="anchored_groups",
                        to="card_reader_core.card",
                    ),
                ),
            ],
            options={"db_table": "card_group"},
        ),
        migrations.CreateModel(
            name="CardGroupMember",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("position", models.IntegerField(db_index=True, default=1)),
                (
                    "card",
                    models.ForeignKey(
                        db_column="card_id",
                        on_delete=models.CASCADE,
                        related_name="card_group_memberships",
                        to="card_reader_core.card",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        db_column="group_id",
                        on_delete=models.CASCADE,
                        related_name="members",
                        to="card_reader_core.cardgroup",
                    ),
                ),
            ],
            options={
                "db_table": "card_group_member",
                "indexes": [models.Index(fields=["card", "position"], name="ix_card_group_member_card_position")],
                "constraints": [
                    models.UniqueConstraint(fields=("group", "card"), name="ux_card_group_member_group_card"),
                    models.UniqueConstraint(fields=("group", "position"), name="ux_card_group_member_group_position"),
                ],
            },
        ),
    ]
