from __future__ import annotations

import logging
from collections.abc import Callable

from django.db import transaction

from card_reader_core.models import Card, CardVersion
from card_reader_core.repositories.cards import (
    promote_card_version,
    update_latest_card_version,
)
from card_reader_core.services.notifications import (
    DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
    NotificationService,
)
from card_reader_core.services.tts_card_sheets import TtsCardSheetService

logger = logging.getLogger(__name__)


def _run_reconciliation_action(*, card_id: str, action_name: str, action: Callable[[], object]) -> None:
    try:
        action()
    except Exception:
        logger.exception(
            "Card classification reconciliation failed",
            extra={"card_id": card_id, "action": action_name},
        )


def _reconcile_card_classification(*, card_id: str) -> None:
    _run_reconciliation_action(
        card_id=card_id,
        action_name="sync_tts_card_sheets",
        action=lambda: TtsCardSheetService().sync_cards([card_id]),
    )


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
    updated = update_latest_card_version(
        card_id=card_id,
        updates=updates,
        restore_fields=restore_fields,
        restore_metadata_groups=restore_metadata_groups,
        unlock_fields=unlock_fields,
        unlock_metadata_groups=unlock_metadata_groups,
    )
    if updated is not None and "card_pool" in updates:
        card, _version = updated
        transaction.on_commit(
            lambda: _reconcile_card_classification(
                card_id=card.id,
            )
        )
    return updated


def promote_card_version_with_notifications(
    *,
    card_id: str,
    version_id: str,
    actor_id: str | None = None,
) -> tuple[Card, CardVersion] | None:
    previous_card_version_id = (
        Card.objects.filter(id=card_id).values_list("latest_version_id", flat=True).first()
    )
    target_was_current_latest = previous_card_version_id == version_id
    promoted = promote_card_version(card_id=card_id, version_id=version_id)
    if promoted is not None and not target_was_current_latest:
        card, version = promoted

        transaction.on_commit(
            lambda: NotificationService().notify_deck_owners_card_version_changed(
                card_id=card.id,
                card_version_id=version.id,
                previous_card_version_id=previous_card_version_id,
                cause=DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
                actor_id=actor_id,
            )
        )
        transaction.on_commit(lambda: TtsCardSheetService().sync_cards([card.id]))
    return promoted
