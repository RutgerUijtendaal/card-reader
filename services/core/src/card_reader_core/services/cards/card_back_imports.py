from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from django.db import IntegrityError, transaction

from card_reader_core.models import CardBackImportReceipt
from card_reader_core.repositories.card_backs import (
    claim_import_receipt,
    finish_import_receipt,
    get_import_receipt,
)
from card_reader_core.repositories.cards import HeroCardBackExpectation
from card_reader_core.services.card_backs import (
    create_prepared_card_back,
    discard_card_back_source,
    prepare_card_back_asset,
)

from .edits import update_latest_card_version_with_notifications


def get_card_back_import_result(
    owner_id: str, client_request_id: UUID
) -> CardBackImportReceipt | None:
    return get_import_receipt(owner_id, client_request_id)


def import_card_back(
    *,
    owner_id: str,
    client_request_id: UUID,
    filename: str,
    chunks: Iterable[bytes],
    label: str,
    hero_card_id: str | None,
    expected_override_id: str | None,
) -> tuple[CardBackImportReceipt, bool]:
    existing = get_import_receipt(owner_id, client_request_id)
    if existing is not None:
        return existing, False

    prepared = None
    preparation_error = ""
    try:
        if not label.strip():
            raise ValueError("A label is required.")
        prepared = prepare_card_back_asset(filename=filename, chunks=chunks, label=label)
    except ValueError as exc:
        preparation_error = str(exc)

    committed_asset = False
    try:
        try:
            with transaction.atomic():
                receipt = claim_import_receipt(owner_id, client_request_id)
                try:
                    with transaction.atomic():
                        if prepared is None:
                            raise ValueError(preparation_error)
                        card_back = create_prepared_card_back(prepared)
                        if hero_card_id is not None:
                            updated = update_latest_card_version_with_notifications(
                                card_id=hero_card_id,
                                updates={"card_back_override_id": card_back.id},
                                restore_fields=[],
                                restore_metadata_groups=[],
                                unlock_fields=[],
                                unlock_metadata_groups=[],
                                actor_id=owner_id,
                                hero_card_back_expectation=HeroCardBackExpectation(
                                    expected_override_id
                                ),
                            )
                            if updated is None:
                                raise ValueError(
                                    "The hero is no longer available. Review this row again."
                                )
                        finish_import_receipt(
                            receipt, card_back=card_back, hero_card_id=hero_card_id
                        )
                except ValueError as exc:
                    # A durable rejection prevents delayed requests from applying this key later.
                    finish_import_receipt(
                        receipt, card_back=None, hero_card_id=hero_card_id, error=str(exc)
                    )
            committed_asset = receipt.card_back_id is not None
            return receipt, True
        except IntegrityError:
            existing = get_import_receipt(owner_id, client_request_id)
            if existing is None:
                raise
            return existing, False
    finally:
        if prepared is not None and not committed_asset:
            discard_card_back_source(prepared.source_file)
