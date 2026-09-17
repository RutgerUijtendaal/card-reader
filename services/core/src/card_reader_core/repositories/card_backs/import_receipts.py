from __future__ import annotations

from uuid import UUID

from card_reader_core.models import CardBack, CardBackImportReceipt


def get_import_receipt(owner_id: str, client_request_id: UUID) -> CardBackImportReceipt | None:
    return (
        CardBackImportReceipt.objects.select_related("card_back")
        .filter(owner_id=owner_id, client_request_id=client_request_id)
        .first()
    )


def claim_import_receipt(owner_id: str, client_request_id: UUID) -> CardBackImportReceipt:
    # The unique insert is the first transaction write, also serializing SQLite writers.
    return CardBackImportReceipt.objects.create(
        owner_id=owner_id, client_request_id=client_request_id
    )


def finish_import_receipt(
    receipt: CardBackImportReceipt,
    *,
    card_back: CardBack | None,
    hero_card_id: str | None,
    error: str = "",
) -> None:
    receipt.card_back = card_back
    receipt.hero_card_id = hero_card_id
    receipt.error = error
    receipt.save(update_fields=["card_back", "hero_card_id", "error"])
