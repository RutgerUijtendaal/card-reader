from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import card_reader_core.models.base


def guard_classification_review_downgrade(apps, _schema_editor) -> None:  # type: ignore[no-untyped-def]
    ReviewItem = apps.get_model("card_reader_core", "CardClassificationReviewItem")
    if ReviewItem.objects.exists():
        raise RuntimeError(
            "Card classification review migration 0057 cannot be reversed while durable "
            "classification review items exist. Preserve or remove those records explicitly "
            "before rolling back."
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("card_reader_core", "0056_card_mana_families"),
    ]

    operations = [
        migrations.CreateModel(
            name="CardClassificationReviewItem",
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
                    "id",
                    models.TextField(
                        default=card_reader_core.models.base.uuid_str,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("card_pool", models.TextField(db_index=True)),
                ("existing_classification_json", models.JSONField(default=dict)),
                ("inferred_classification_json", models.JSONField(default=dict)),
                ("inference_evidence_json", models.JSONField(default=dict)),
                ("status", models.TextField(db_index=True, default="open")),
                ("review_note", models.TextField(blank=True, default="")),
                (
                    "reviewed_at",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
                (
                    "card",
                    models.ForeignKey(
                        blank=True,
                        db_column="card_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="classification_review_items",
                        to="card_reader_core.card",
                    ),
                ),
                (
                    "card_version",
                    models.ForeignKey(
                        blank=True,
                        db_column="card_version_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="classification_review_items",
                        to="card_reader_core.cardversion",
                    ),
                ),
                (
                    "import_item",
                    models.OneToOneField(
                        db_column="import_item_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="classification_review_item",
                        to="card_reader_core.importjobitem",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="reviewed_by_id",
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_card_classification_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "card_classification_review_item",
                "indexes": [
                    models.Index(
                        fields=["status", "created_at"],
                        name="ix_class_review_status_created",
                    ),
                    models.Index(
                        fields=["card_pool", "status"],
                        name="ix_class_review_pool_status",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            migrations.RunPython.noop,
            guard_classification_review_downgrade,
        ),
    ]
