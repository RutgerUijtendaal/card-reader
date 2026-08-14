from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from card_reader_api.seeds.notification_examples import (
    EXAMPLE_DECK_NAME,
    seed_notification_examples,
)
from card_reader_core.config import settings
from card_reader_core.models import (
    NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED,
    NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
    ALL_CARD_POOLS_SCOPE,
    Card,
    CardRoleAssignment,
    CardVersion,
    CardVersionImage,
    Deck,
    Template,
    UserNotification,
)
from card_reader_core.repositories.notifications import set_notification_read_state


def test_notification_examples_seed_real_layout_data_idempotently() -> None:
    user = get_user_model().objects.create_user(
        username="notification-layout-admin",
        password="ValidPassword123!",
        is_staff=True,
    )
    _create_versioned_card(
        key="0-notification-gm-hero",
        name="Notification GM Hero",
        hero=True,
        with_history=False,
        card_pool="evil",
    )
    _create_versioned_card(
        key="0-notification-gm-change",
        name="Notification GM Change",
        hero=False,
        card_pool="evil",
    )
    hero, _hero_previous, _hero_current = _create_versioned_card(
        key="z-notification-hero",
        name="Notification Hero",
        hero=True,
        with_history=False,
    )
    card, previous, current = _create_versioned_card(
        key="a-notification-change",
        name="Notification Change",
        hero=False,
    )

    first = seed_notification_examples(username=user.username)
    second = seed_notification_examples(username=user.username)

    assert first.created_notifications == 2
    assert first.existing_notifications == 0
    assert first.created_decks == 1
    assert second.created_notifications == 0
    assert second.existing_notifications == 2
    assert second.created_decks == 0
    assert UserNotification.objects.filter(recipient=user).count() == 2

    deck = Deck.objects.get(owner=user, name=EXAMPLE_DECK_NAME)
    assert deck.hero_card_id == hero.id
    assert list(deck.entries.values_list("card_id", "quantity")) == [(card.id, 1)]

    card_change = UserNotification.objects.get(
        recipient=user,
        event_type=NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED,
    )
    assert previous is not None
    assert card_change.target_url == f"/my/decks/{deck.id}"
    assert card_change.metadata_json["previous_card_version_id"] == previous.id
    assert card_change.metadata_json["card_version_id"] == current.id
    assert card_change.event_count == 1

    flag_review = UserNotification.objects.get(
        recipient=user,
        event_type=NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
    )
    assert flag_review.metadata_json["status"] == "resolved"
    assert flag_review.metadata_json["review_note"]

    set_notification_read_state(
        notification_id=card_change.id,
        recipient_id=str(user.pk),
        card_pool_scope=ALL_CARD_POOLS_SCOPE,
        read=True,
    )
    third = seed_notification_examples(username=user.username)

    assert third.created_notifications == 0
    assert third.existing_notifications == 2
    assert UserNotification.objects.filter(recipient=user).count() == 2


def test_notification_examples_are_disabled_outside_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "production")

    with pytest.raises(CommandError, match="disabled outside development"):
        call_command("seed_notification_examples")


def _create_versioned_card(
    *,
    key: str,
    name: str,
    hero: bool,
    with_history: bool = True,
    card_pool: str = "player",
) -> tuple[Card, CardVersion | None, CardVersion]:
    template = Template.objects.get(key="mtg-like-v1")
    card = Card.objects.create(key=key, label=name, card_pool=card_pool)
    if hero:
        CardRoleAssignment.objects.create(card=card, role="hero")
    previous = (
        _create_card_version(
            card=card,
            template=template,
            version_number=1,
            name=name,
            is_latest=False,
        )
        if with_history
        else None
    )
    current = _create_card_version(
        card=card,
        template=template,
        version_number=2 if previous is not None else 1,
        name=name,
        is_latest=True,
        previous=previous,
    )
    card.latest_version = current
    card.save(update_fields=["latest_version"])
    return card, previous, current


def _create_card_version(
    *,
    card: Card,
    template: Template,
    version_number: int,
    name: str,
    is_latest: bool,
    previous: CardVersion | None = None,
) -> CardVersion:
    version = CardVersion.objects.create(
        card=card,
        version_number=version_number,
        template=template,
        image_hash=f"{card.key}-{version_number}",
        name=name,
        type_line="Hero" if card.role_assignments.filter(role="hero").exists() else "Persistent Spell",
        mana_cost="1",
        mana_symbols_json=[],
        mana_value=1,
        rules_text_raw="Example rules text.",
        rules_text_enriched="Example rules text.",
        rules_text="Example rules text.",
        confidence=1,
        field_sources_json={"fields": {}, "metadata": {}},
        parsed_snapshot_json={"fields": {}, "metadata": {}},
        is_latest=is_latest,
        previous_version=previous,
    )
    CardVersionImage.objects.create(
        card_version=version,
        source_file=f"{card.key}-{version_number}.png",
        stored_path=f"images/{card.key}-{version_number}.webp",
        width=630,
        height=880,
        checksum=f"checksum-{card.key}-{version_number}",
    )
    return version
