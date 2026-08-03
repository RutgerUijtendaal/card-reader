from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from card_reader_core.config import settings
from card_reader_core.models import (
    NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED,
    NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
    Card,
    CardVersionParseFlagItem,
    Deck,
    UserNotification,
)
from card_reader_core.repositories.notifications import NotificationInput, create_or_coalesce_notification

from .types import (
    DECK_CARD_VERSION_CHANGE_IMPORT_CREATED,
    DeckCardVersionChangeCause,
    DeckCardVersionChangedMetadata,
    NotificationEvent,
    ParseFlagItemReviewedMetadata,
    ParseFlagReviewStatus,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class NotificationService:
    def notify(self, event: NotificationEvent) -> UserNotification:
        return create_or_coalesce_notification(
            NotificationInput(
                recipient_id=event.recipient_id,
                actor_id=event.actor_id,
                event_type=event.event_type,
                subject_type=event.subject_type,
                subject_id=event.subject_id,
                target_url=event.target_url,
                title=event.title,
                message=event.message,
                metadata=event.metadata,
                dedupe_key=event.dedupe_key,
            )
        )

    def notify_parse_flag_reviewed(self, item: CardVersionParseFlagItem) -> UserNotification | None:
        flag = item.flag
        submitted_by_id = str(getattr(flag.submitted_by, "pk", ""))
        reviewer_id = str(getattr(item.reviewed_by, "pk", "")) if item.reviewed_by is not None else None
        is_self_review = submitted_by_id == reviewer_id
        if not submitted_by_id or (is_self_review and not settings.is_dev):
            return None

        version = flag.card_version
        card = version.card
        status_label: ParseFlagReviewStatus = "resolved" if item.status == "resolved" else "dismissed"
        reviewer_name = _username(item.reviewed_by)
        flag_item_label = _parse_flag_item_label(item.property_key)
        title = f"Flag {status_label}: {version.name or card.label}"
        message = (
            f"{reviewer_name} {status_label} your {flag_item_label}."
            if reviewer_name
            else f"Your {flag_item_label} was {status_label}."
        )
        return self.notify(
            NotificationEvent(
                recipient_id=submitted_by_id,
                actor_id=reviewer_id,
                event_type=NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
                subject_type="parse_flag_item",
                subject_id=item.id,
                target_url=f"/cards/{card.id}?version_id={version.id}",
                title=title,
                message=message,
                metadata=ParseFlagItemReviewedMetadata(
                    card_id=card.id,
                    card_name=version.name or card.label,
                    card_version_id=version.id,
                    flag_id=flag.id,
                    property_key=item.property_key,
                    property_label=flag_item_label,
                    status=status_label,
                    submitted_value=item.expected_value,
                    submission_note=item.note or flag.note,
                    reviewer_name=reviewer_name,
                    review_note=item.review_note,
                ).as_dict(),
                dedupe_key=f"{NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED}:{item.id}",
            )
        )

    def notify_deck_owners_card_version_changed(
        self,
        *,
        card_id: str,
        card_version_id: str,
        previous_card_version_id: str | None,
        cause: DeckCardVersionChangeCause,
        actor_id: str | None = None,
        import_job_id: str | None = None,
        import_item_id: str | None = None,
    ) -> list[UserNotification]:
        card = Card.objects.filter(id=card_id).first()
        if card is None:
            return []

        decks = (
            Deck.objects.select_related("owner", "hero_card")
            .filter(Q(hero_card_id=card.id) | Q(entries__card_id=card.id) | Q(sideboards__entries__card_id=card.id))
            .distinct()
            .order_by("owner_id", "id")
        )
        notifications: list[UserNotification] = []
        for deck in decks:
            owner_id = str(getattr(deck.owner, "pk", ""))
            if not owner_id or owner_id == actor_id:
                continue
            card_name = card.label
            title = f"Card version changed in {deck.name}"
            message = _deck_card_version_change_message(card_name, cause)
            notifications.append(
                self.notify(
                    NotificationEvent(
                        recipient_id=owner_id,
                        actor_id=actor_id,
                        event_type=NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED,
                        subject_type="deck_card",
                        subject_id=f"{deck.id}:{card.id}",
                        target_url=f"/my/decks/{deck.id}",
                        title=title,
                        message=message,
                        metadata=DeckCardVersionChangedMetadata(
                            deck_id=deck.id,
                            deck_name=deck.name,
                            card_id=card.id,
                            card_name=card_name,
                            card_version_id=card_version_id,
                            previous_card_version_id=previous_card_version_id,
                            change_cause=cause,
                            import_job_id=import_job_id,
                            import_item_id=import_item_id,
                        ).as_dict(),
                        dedupe_key=f"{NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED}:{deck.id}:{card.id}",
                    )
                )
            )
        return notifications


def _username(user: AbstractUser | None) -> str:
    if user is None:
        return ""
    return user.get_username()


def _parse_flag_item_label(property_key: str) -> str:
    if property_key == "overall":
        return "overall suggestion"
    return f"{property_key.replace('_', ' ')} flag"


def _deck_card_version_change_message(card_name: str, cause: DeckCardVersionChangeCause) -> str:
    if cause == DECK_CARD_VERSION_CHANGE_IMPORT_CREATED:
        return f"A newly imported version of {card_name} is now current and appears in your deck."
    if cause == "version_promoted":
        return f"A different version of {card_name} was promoted to current and appears in your deck."
    raise ValueError(f"Unsupported deck card version change cause: {cause}")
