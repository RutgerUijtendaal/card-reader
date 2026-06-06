from __future__ import annotations

from typing import ClassVar

import card_reader_core.models.base
import django.db.models.deletion
from django.db import migrations, models


def backfill_content_versions(apps, _schema_editor) -> None:  # type: ignore[no-untyped-def]
    ContentVersion = apps.get_model("card_reader_core", "ContentVersion")
    CardVersion = apps.get_model("card_reader_core", "CardVersion")

    latest_count = CardVersion.objects.filter(is_latest=True).count()
    if latest_count:
        current, _created = ContentVersion.objects.get_or_create(
            version_number="1.0.0",
            defaults={
                "base_version": "1.0",
                "major": 1,
                "minor": 0,
                "patch": 0,
                "description": "Backfilled current version.",
            },
        )
        CardVersion.objects.filter(is_latest=True).update(content_version_id=current.id)

    historical_generations = (
        CardVersion.objects.filter(is_latest=False)
        .values_list("version_number", flat=True)
        .distinct()
        .order_by("version_number")
    )
    for generation in historical_generations:
        version_number = f"0.{generation}.0"
        historical, _created = ContentVersion.objects.get_or_create(
            version_number=version_number,
            defaults={
                "base_version": f"0.{generation}",
                "major": 0,
                "minor": generation,
                "patch": 0,
                "description": f"Backfilled historical card generation {generation}.",
            },
        )
        CardVersion.objects.filter(is_latest=False, version_number=generation).update(
            content_version_id=historical.id
        )


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("card_reader_core", "0027_card_deck_building_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentVersion",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("version_number", models.TextField(unique=True)),
                ("base_version", models.TextField(db_index=True)),
                ("major", models.IntegerField(db_index=True)),
                ("minor", models.IntegerField(db_index=True)),
                ("patch", models.IntegerField(db_index=True)),
                ("description", models.TextField()),
            ],
            options={
                "db_table": "content_version",
            },
        ),
        migrations.AddField(
            model_name="importjob",
            name="content_version",
            field=models.ForeignKey(
                blank=True,
                db_column="content_version_id",
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="import_jobs",
                to="card_reader_core.contentversion",
            ),
        ),
        migrations.AddField(
            model_name="cardversion",
            name="content_version",
            field=models.ForeignKey(
                blank=True,
                db_column="content_version_id",
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="card_versions",
                to="card_reader_core.contentversion",
            ),
        ),
        migrations.AddIndex(
            model_name="contentversion",
            index=models.Index(fields=["major", "minor", "patch"], name="ix_content_version_semver"),
        ),
        migrations.AddConstraint(
            model_name="contentversion",
            constraint=models.UniqueConstraint(
                fields=("major", "minor", "patch"),
                name="ux_content_version_semver",
            ),
        ),
        migrations.RunPython(backfill_content_versions, migrations.RunPython.noop),
    ]
