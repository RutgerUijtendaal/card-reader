from __future__ import annotations

from card_reader_core.models import Card, CardVersion
from card_reader_core.repositories.cards import (
    promote_card_version,
    update_latest_card_version,
)
from card_reader_core.services.notifications import NotificationService


def update_latest_card_version_with_notifications(
    *,
    card_id: str,
    updates: dict[str, object],
    restore_fields: list[str],
    restore_metadata_groups: list[str],
    unlock_fields: list[str],
    unlock_metadata_groups: list[str],
    actor_id: str | None = None,
) -> tuple[Card, CardVersion] | None:
    return update_latest_card_version(
        card_id=card_id,
        updates=updates,
        restore_fields=restore_fields,
        restore_metadata_groups=restore_metadata_groups,
        unlock_fields=unlock_fields,
        unlock_metadata_groups=unlock_metadata_groups,
    )


def promote_card_version_with_notifications(
    *,
    card_id: str,
    version_id: str,
    actor_id: str | None = None,
) -> tuple[Card, CardVersion] | None:
    promoted = promote_card_version(card_id=card_id, version_id=version_id)
    if promoted is not None:
        card, _version = promoted
        from django.db import transaction

        transaction.on_commit(
            lambda: NotificationService().notify_deck_owners_card_changed(
                card_id=card.id,
                actor_id=actor_id,
                change_label="promoted",
            )
        )
    return promoted
