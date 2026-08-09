from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model

from card_reader_core.models import (
    ACTIVE_CARD_LIFECYCLE_STATUS,
    NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
    Card,
    CardVersion,
    Deck,
    UserNotification,
)
from card_reader_core.services.decks import DeckEntryInput, DeckService, DeckUpdateInput
from card_reader_core.services.notifications import (
    DECK_CARD_VERSION_CHANGE_IMPORT_CREATED,
    NotificationEvent,
    NotificationService,
    ParseFlagItemReviewedMetadata,
)

EXAMPLE_DECK_NAME = "Notification Layout Examples"
FLAG_EXAMPLE_DEDUPE_KEY = "dev-example:parse-flag-reviewed"


@dataclass(frozen=True)
class NotificationExampleSeedResult:
    recipients: int
    created_notifications: int
    existing_notifications: int
    created_decks: int
    updated_decks: int
    skipped_recipients: int


def seed_notification_examples(*, username: str | None = None) -> NotificationExampleSeedResult:
    recipients = _notification_example_recipients(username=username)
    comparison_version = _comparison_version()
    reference_version = comparison_version or _reference_version()
    hero_card = _hero_card(comparison_version)
    service = NotificationService()
    created_notifications = 0
    existing_notifications = 0
    created_decks = 0
    updated_decks = 0
    skipped_recipients = 0

    for recipient in recipients:
        recipient_id = str(recipient.pk)
        recipient_created = 0

        if reference_version is not None:
            created = _ensure_flag_review_example(
                service=service,
                recipient_id=recipient_id,
                version=reference_version,
            )
            created_notifications += int(created)
            existing_notifications += int(not created)
            recipient_created += int(created)

        if comparison_version is not None and hero_card is not None:
            deck, deck_created, deck_updated = _ensure_example_deck(
                recipient_id=recipient_id,
                hero_card=hero_card,
                compared_card=comparison_version.card,
            )
            created_decks += int(deck_created)
            updated_decks += int(deck_updated)
            created = _ensure_card_version_change_example(
                service=service,
                deck=deck,
                version=comparison_version,
            )
            created_notifications += int(created)
            existing_notifications += int(not created)
            recipient_created += int(created)

        if recipient_created == 0 and reference_version is None:
            skipped_recipients += 1

    return NotificationExampleSeedResult(
        recipients=len(recipients),
        created_notifications=created_notifications,
        existing_notifications=existing_notifications,
        created_decks=created_decks,
        updated_decks=updated_decks,
        skipped_recipients=skipped_recipients,
    )


def _notification_example_recipients(*, username: str | None) -> list[Any]:
    queryset = get_user_model().objects.filter(is_active=True, is_staff=True)
    if username is not None:
        queryset = queryset.filter(username=username)
    return list(queryset.order_by("username"))


def _comparison_version() -> CardVersion | None:
    return (
        CardVersion.objects.select_related("card", "previous_version")
        .filter(
            card__lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
            is_latest=True,
            images__isnull=False,
            previous_version__images__isnull=False,
        )
        .distinct()
        .order_by("card__key", "version_number")
        .first()
    )


def _reference_version() -> CardVersion | None:
    return (
        CardVersion.objects.select_related("card")
        .filter(
            card__lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
            is_latest=True,
            images__isnull=False,
        )
        .distinct()
        .order_by("card__key", "version_number")
        .first()
    )


def _hero_card(comparison_version: CardVersion | None) -> Card | None:
    if comparison_version is not None and comparison_version.card.is_hero:
        return comparison_version.card
    return (
        Card.objects.filter(
            is_hero=True,
            lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS,
            latest_version__images__isnull=False,
        )
        .distinct()
        .order_by("key")
        .first()
    )


def _ensure_example_deck(
    *,
    recipient_id: str,
    hero_card: Card,
    compared_card: Card,
) -> tuple[Deck, bool, bool]:
    entries = [] if hero_card.id == compared_card.id else [DeckEntryInput(card_id=compared_card.id, quantity=1)]
    deck = Deck.objects.filter(owner_id=recipient_id, name=EXAMPLE_DECK_NAME).first()
    deck_service = DeckService()
    if deck is None:
        created_deck = deck_service.create_owner_deck(
            owner_id=recipient_id,
            name=EXAMPLE_DECK_NAME,
            description="Development-only deck used by the notification inbox examples.",
            visibility="private",
            hero_card_id=hero_card.id,
            entries=entries,
            sideboards=[],
        )
        return created_deck, True, False

    has_expected_cards = (
        deck.hero_card.id == hero_card.id
        and list(deck.entries.order_by("position").values_list("card_id", "quantity"))
        == [(entry.card_id, entry.quantity) for entry in entries]
    )
    if has_expected_cards:
        return deck, False, False

    updated_deck = deck_service.update_owner_deck(
        deck_id=deck.id,
        owner_id=recipient_id,
        updates=DeckUpdateInput(
            hero_card_id=hero_card.id,
            entries=entries,
            sideboards=[],
            update_hero_card_id=True,
            update_entries=True,
            update_sideboards=True,
        ),
    )
    if updated_deck is None:
        raise RuntimeError(f"Could not update development notification deck {deck.id}.")
    return updated_deck, False, True


def _ensure_card_version_change_example(
    *,
    service: NotificationService,
    deck: Deck,
    version: CardVersion,
) -> bool:
    previous_version = version.previous_version
    if previous_version is None:
        return False
    dedupe_key = f"deck.card_version_changed:{deck.id}:{version.card.id}"
    if _example_notification_exists(recipient_id=str(deck.owner.pk), dedupe_key=dedupe_key):
        return False
    notification = service.notify_deck_owner_card_version_changed(
        deck=deck,
        card=version.card,
        card_version_id=version.id,
        previous_card_version_id=previous_version.id,
        cause=DECK_CARD_VERSION_CHANGE_IMPORT_CREATED,
    )
    return notification is not None


def _ensure_flag_review_example(
    *,
    service: NotificationService,
    recipient_id: str,
    version: CardVersion,
) -> bool:
    if _example_notification_exists(recipient_id=recipient_id, dedupe_key=FLAG_EXAMPLE_DEDUPE_KEY):
        return False
    card_name = version.name or version.card.label
    service.notify(
        NotificationEvent(
            recipient_id=recipient_id,
            event_type=NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
            subject_type="dev_notification_example",
            subject_id="parse-flag-reviewed",
            target_url=f"/cards/{version.card.id}?version_id={version.id}",
            title=f"Flag resolved: {card_name}",
            message="Development Reviewer resolved your rules text flag.",
            metadata=ParseFlagItemReviewedMetadata(
                card_id=version.card.id,
                card_name=card_name,
                card_version_id=version.id,
                flag_id="dev-example-parse-flag",
                property_key="rules_text",
                property_label="rules text flag",
                status="resolved",
                submitted_value="Use the corrected wording shown in this development example.",
                submission_note=(
                    "This longer sample note exercises wrapping and spacing in the expanded notification details."
                ),
                reviewer_name="Development Reviewer",
                review_note=(
                    "Accepted for the example inbox. The response is intentionally long enough to test multi-line layout."
                ),
            ).as_dict(),
            dedupe_key=FLAG_EXAMPLE_DEDUPE_KEY,
        )
    )
    return True


def _example_notification_exists(*, recipient_id: str, dedupe_key: str) -> bool:
    return UserNotification.objects.filter(
        recipient_id=recipient_id,
        dedupe_key=dedupe_key,
    ).exists()
