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
from card_reader_core.services.card_backs import select_card_back_override
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
    def sync_tts_card_sheets() -> None:
        TtsCardSheetService().sync_cards([card_id])

    _run_reconciliation_action(
        card_id=card_id,
        action_name="sync_tts_card_sheets",
        action=sync_tts_card_sheets,
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
    resolved_updates = dict(updates)
    if "card_back_override_id" in resolved_updates:
        raw_card_back_id = resolved_updates.pop("card_back_override_id")
        resolved_updates["card_back_override"] = select_card_back_override(
            str(raw_card_back_id) if raw_card_back_id is not None else None
        )
    updated = update_latest_card_version(
        card_id=card_id,
        updates=resolved_updates,
        restore_fields=restore_fields,
        restore_metadata_groups=restore_metadata_groups,
        unlock_fields=unlock_fields,
        unlock_metadata_groups=unlock_metadata_groups,
    )
    if updated is not None and "card_pool" in resolved_updates:
        card, _version = updated

        def reconcile_card_classification() -> None:
            _reconcile_card_classification(card_id=card.id)

        transaction.on_commit(reconcile_card_classification)
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

        def notify_deck_owners() -> None:
            NotificationService().notify_deck_owners_card_version_changed(
                card_id=card.id,
                card_version_id=version.id,
                previous_card_version_id=previous_card_version_id,
                cause=DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
                actor_id=actor_id,
            )

        def sync_tts_card_sheets() -> None:
            TtsCardSheetService().sync_cards([card.id])

        transaction.on_commit(notify_deck_owners)
        transaction.on_commit(sync_tts_card_sheets)
    return promoted
