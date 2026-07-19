from __future__ import annotations

from uuid import uuid4

import card_reader_core.models.base
import django.db.models.deletion
from django.db import migrations, models


DEFAULT_DECK_TAGS = {
    "role": ["Damage", "Healing", "Control", "Tank", "Support"],
    "type": ["Countermagic", "Armor", "Team Card Draw", "New Player"],
}


def _tag_key(label: str) -> str:
    return label.lower().replace(" ", "-")


def seed_deck_tags(apps, _schema_editor) -> None:
    deck_tag = apps.get_model("card_reader_core", "DeckTag")
    for kind, labels in DEFAULT_DECK_TAGS.items():
        for label in labels:
            deck_tag.objects.get_or_create(
                kind=kind,
                key=_tag_key(label),
                defaults={"id": str(uuid4()), "label": label},
            )


def remove_seeded_deck_tags(apps, _schema_editor) -> None:
    deck_tag = apps.get_model("card_reader_core", "DeckTag")
    for kind, labels in DEFAULT_DECK_TAGS.items():
        deck_tag.objects.filter(kind=kind, key__in=[_tag_key(label) for label in labels]).delete()


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0037_user_activity")]

    operations = [
        migrations.CreateModel(
            name="DeckTag",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("kind", models.CharField(choices=[("role", "Role"), ("type", "Type")], db_index=True, max_length=16)),
                ("key", models.TextField(db_index=True, default="")),
                ("label", models.TextField(default="")),
            ],
            options={
                "db_table": "deck_tag",
                "ordering": ["kind", "label", "id"],
                "constraints": [models.UniqueConstraint(fields=("kind", "key"), name="ux_deck_tag_kind_key")],
            },
        ),
        migrations.CreateModel(
            name="DeckTagSuggestion",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("kind", models.CharField(choices=[("type", "Type")], db_index=True, default="type", max_length=16)),
                ("normalized_value", models.TextField(db_index=True, default="")),
                ("display_value", models.TextField(default="")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")], db_index=True, default="pending", max_length=16)),
                ("accepted_tag", models.ForeignKey(blank=True, db_column="accepted_tag_id", default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accepted_suggestions", to="card_reader_core.decktag")),
            ],
            options={
                "db_table": "deck_tag_suggestion",
                "ordering": ["status", "display_value", "id"],
                "constraints": [models.UniqueConstraint(fields=("kind", "normalized_value"), name="ux_deck_tag_suggestion_kind_value")],
            },
        ),
        migrations.CreateModel(
            name="DeckTagAssignment",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("deck", models.ForeignKey(db_column="deck_id", on_delete=django.db.models.deletion.CASCADE, related_name="tag_assignments", to="card_reader_core.deck")),
                ("tag", models.ForeignKey(db_column="tag_id", on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="card_reader_core.decktag")),
            ],
            options={
                "db_table": "deck_tag_assignment",
                "ordering": ["tag__kind", "tag__label", "id"],
                "indexes": [models.Index(fields=["tag", "deck"], name="ix_deck_tag_assignment_tag")],
                "constraints": [models.UniqueConstraint(fields=("deck", "tag"), name="ux_deck_tag_assignment_pair")],
            },
        ),
        migrations.CreateModel(
            name="DeckTagSuggestionDeck",
            fields=[
                ("created_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("updated_at", models.DateTimeField(default=card_reader_core.models.base.now_utc)),
                ("id", models.TextField(default=card_reader_core.models.base.uuid_str, primary_key=True, serialize=False)),
                ("deck", models.ForeignKey(db_column="deck_id", on_delete=django.db.models.deletion.CASCADE, related_name="tag_suggestion_occurrences", to="card_reader_core.deck")),
                ("suggestion", models.ForeignKey(db_column="suggestion_id", on_delete=django.db.models.deletion.CASCADE, related_name="deck_occurrences", to="card_reader_core.decktagsuggestion")),
            ],
            options={
                "db_table": "deck_tag_suggestion_deck",
                "indexes": [models.Index(fields=["deck", "suggestion"], name="ix_deck_tag_suggestion_deck")],
                "constraints": [models.UniqueConstraint(fields=("suggestion", "deck"), name="ux_deck_tag_suggestion_deck_pair")],
            },
        ),
        migrations.RunPython(seed_deck_tags, remove_seeded_deck_tags),
    ]
