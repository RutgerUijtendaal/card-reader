from __future__ import annotations

import pytest

from card_reader_core.models import Card, CardLifecycleStatus, CardPool, CardVersion, Template
from card_reader_core.repositories.cards import list_card_link_suggestions


@pytest.mark.django_db
def test_card_link_suggestions_rank_preferred_pool_then_name_relevance() -> None:
    template = Template.objects.create(key="link-suggestion-template", label="Link suggestions")
    _create_card_version(template, name="Blessing of Giants", card_pool="player")
    _create_card_version(template, name="Unblessed", card_pool="player")
    _create_card_version(template, name="BLESS", card_pool="player")
    _create_card_version(template, name="Blessed", card_pool="player")
    _create_card_version(template, name="Bless", card_pool="evil")
    _create_card_version(template, name="Blessing", card_pool="evil")

    suggestions = list_card_link_suggestions(
        query="bless",
        preferred_card_pool="player",
    )

    assert [(row.version.card.card_pool, row.version.name) for row in suggestions] == [
        ("player", "BLESS"),
        ("player", "Blessed"),
        ("player", "Blessing of Giants"),
        ("player", "Unblessed"),
        ("evil", "Bless"),
        ("evil", "Blessing"),
    ]


@pytest.mark.django_db
def test_card_link_suggestions_search_names_and_respect_lifecycle_and_limit() -> None:
    template = Template.objects.create(key="link-suggestion-filter-template", label="Filters")
    _create_card_version(
        template,
        name="Irrelevant",
        card_pool="player",
        rules_text="Bless appears only in rules text.",
    )
    _create_card_version(
        template,
        name="Bless Deprecated",
        card_pool="player",
        lifecycle_status="deprecated",
    )
    for index in range(10):
        _create_card_version(
            template,
            name=f"Bless Candidate {index}",
            card_pool="player",
        )

    active_suggestions = list_card_link_suggestions(
        query="Bless",
        preferred_card_pool="player",
        limit=20,
    )
    all_suggestions = list_card_link_suggestions(
        query="Bless",
        preferred_card_pool="player",
        lifecycle_status="all",
        limit=8,
    )

    assert len(active_suggestions) == 8
    assert all(row.version.name != "Irrelevant" for row in active_suggestions)
    assert all(row.version.name != "Bless Deprecated" for row in active_suggestions)
    assert "Bless Deprecated" in [row.version.name for row in all_suggestions]


def _create_card_version(
    template: Template,
    *,
    name: str,
    card_pool: CardPool,
    lifecycle_status: CardLifecycleStatus = "active",
    rules_text: str = "",
) -> CardVersion:
    key = name.lower().replace(" ", "-")
    card = Card.objects.create(
        key=key,
        label=name,
        card_pool=card_pool,
        lifecycle_status=lifecycle_status,
    )
    version = CardVersion.objects.create(
        card=card,
        template=template,
        image_hash=f"hash-{card_pool}-{key}",
        name=name,
        rules_text=rules_text,
        is_latest=True,
    )
    card.latest_version = version
    card.save(update_fields=["latest_version"])
    return version
