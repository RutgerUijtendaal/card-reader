from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from card_reader_core.models import (
    NOTIFICATION_EVENT_DECK_CARD_CHANGED,
    NOTIFICATION_EVENT_PARSE_FLAG_REVIEWED,
    Card,
    CardVersionParseFlagItem,
    Deck,
    UserNotification,
)
from card_reader_core.repositories.notifications import NotificationInput, create_or_coalesce_notification

from .types import NotificationEvent

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
        if not submitted_by_id or submitted_by_id == reviewer_id:
            return None

        version = flag.card_version
        card = version.card
        status_label = "resolved" if item.status == "resolved" else "dismissed"
        reviewer_name = _username(item.reviewed_by)
        title = f"Flag {status_label}: {version.name or card.label}"
        message = (
            f"{reviewer_name} {status_label} your {item.property_key.replace('_', ' ')} flag."
            if reviewer_name
            else f"Your {item.property_key.replace('_', ' ')} flag was {status_label}."
        )
        return self.notify(
            NotificationEvent(
                recipient_id=submitted_by_id,
                actor_id=reviewer_id,
                event_type=NOTIFICATION_EVENT_PARSE_FLAG_REVIEWED,
                subject_type="parse_flag_item",
                subject_id=item.id,
                target_url=f"/cards/{card.id}",
                title=title,
                message=message,
                metadata={
                    "card_id": card.id,
                    "card_name": version.name or card.label,
                    "card_version_id": version.id,
                    "flag_id": flag.id,
                    "property_key": item.property_key,
                    "status": item.status,
                    "review_note": item.review_note,
                },
                dedupe_key=f"{NOTIFICATION_EVENT_PARSE_FLAG_REVIEWED}:{item.id}",
            )
        )

    def notify_deck_owners_card_changed(
        self,
        *,
        card_id: str,
        actor_id: str | None = None,
        change_label: str = "updated",
        metadata: dict[str, object] | None = None,
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
            title = f"Card changed in {deck.name}"
            message = f"{card_name} was {change_label} and appears in your deck."
            notifications.append(
                self.notify(
                    NotificationEvent(
                        recipient_id=owner_id,
                        actor_id=actor_id,
                        event_type=NOTIFICATION_EVENT_DECK_CARD_CHANGED,
                        subject_type="deck_card",
                        subject_id=f"{deck.id}:{card.id}",
                        target_url=f"/my/decks/{deck.id}",
                        title=title,
                        message=message,
                        metadata={
                            "deck_id": deck.id,
                            "deck_name": deck.name,
                            "card_id": card.id,
                            "card_name": card_name,
                            "change_label": change_label,
                            **(metadata or {}),
                        },
                        dedupe_key=f"{NOTIFICATION_EVENT_DECK_CARD_CHANGED}:{deck.id}:{card.id}",
                    )
                )
            )
        return notifications


def _username(user: AbstractUser | None) -> str:
    if user is None:
        return ""
    return user.get_username()
