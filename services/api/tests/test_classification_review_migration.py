from __future__ import annotations

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest

pytestmark = pytest.mark.migration_state


MANA_MIGRATION = ("card_reader_core", "0056_card_mana_families")
REVIEW_MIGRATION = ("card_reader_core", "0057_card_classification_review_item")


def _migrate_to(target: tuple[str, str]):
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


def _restore_leaf() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_review_migration_refuses_to_drop_durable_classification_evidence() -> None:
    apps = _migrate_to(REVIEW_MIGRATION)
    Card = apps.get_model("card_reader_core", "Card")
    CardVersion = apps.get_model("card_reader_core", "CardVersion")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")
    ReviewItem = apps.get_model("card_reader_core", "CardClassificationReviewItem")
    Template = apps.get_model("card_reader_core", "Template")

    template = Template.objects.get(key="mtg-like-v1")
    card = Card.objects.create(
        key="review-rollback-card",
        label="Review Rollback Card",
        card_pool="player",
    )
    version = CardVersion.objects.create(
        card_id=card.id,
        template_id=template.id,
        name="Review Rollback Card",
        image_hash="review-rollback-hash",
    )
    card.latest_version_id = version.id
    card.save(update_fields=["latest_version"])
    job = ImportJob.objects.create(
        source_path="imports/review-rollback",
        template_id=template.id,
        card_pool="player",
    )
    item = ImportJobItem.objects.create(
        job_id=job.id,
        source_file="imports/review-rollback/card.png",
        target_card_id=card.id,
        target_card_version_id=version.id,
    )
    review = ReviewItem.objects.create(
        import_item_id=item.id,
        card_id=card.id,
        card_version_id=version.id,
        card_pool="player",
        existing_classification_json={"card_pool": "player"},
        inferred_classification_json={"card_pool": "evil"},
        inference_evidence_json={"reason": "rollback regression"},
    )

    try:
        with pytest.raises(RuntimeError, match="durable classification review items"):
            _migrate_to(MANA_MIGRATION)
        assert ReviewItem.objects.filter(id=review.id).exists()

        ReviewItem.objects.filter(id=review.id).delete()
        _migrate_to(MANA_MIGRATION)
    finally:
        _restore_leaf()
