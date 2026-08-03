from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DeckCardVersionChangeCause = Literal["import_created", "version_promoted"]
ParseFlagReviewStatus = Literal["resolved", "dismissed"]

DECK_CARD_VERSION_CHANGE_IMPORT_CREATED: DeckCardVersionChangeCause = "import_created"
DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED: DeckCardVersionChangeCause = "version_promoted"


@dataclass(frozen=True)
class ParseFlagItemReviewedMetadata:
    card_id: str
    card_name: str
    card_version_id: str
    flag_id: str
    property_key: str
    property_label: str
    status: ParseFlagReviewStatus
    submitted_value: str
    submission_note: str
    reviewer_name: str
    review_note: str

    def as_dict(self) -> dict[str, object]:
        return {
            "card_id": self.card_id,
            "card_name": self.card_name,
            "card_version_id": self.card_version_id,
            "flag_id": self.flag_id,
            "property_key": self.property_key,
            "property_label": self.property_label,
            "status": self.status,
            "submitted_value": self.submitted_value,
            "submission_note": self.submission_note,
            "reviewer_name": self.reviewer_name,
            "review_note": self.review_note,
        }


@dataclass(frozen=True)
class DeckCardVersionChangedMetadata:
    deck_id: str
    deck_name: str
    card_id: str
    card_name: str
    card_version_id: str
    previous_card_version_id: str | None
    change_cause: DeckCardVersionChangeCause
    import_job_id: str | None = None
    import_item_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        metadata: dict[str, object] = {
            "deck_id": self.deck_id,
            "deck_name": self.deck_name,
            "card_id": self.card_id,
            "card_name": self.card_name,
            "card_version_id": self.card_version_id,
            "change_cause": self.change_cause,
        }
        if self.previous_card_version_id is not None:
            metadata["previous_card_version_id"] = self.previous_card_version_id
        if self.import_job_id is not None:
            metadata["import_job_id"] = self.import_job_id
        if self.import_item_id is not None:
            metadata["import_item_id"] = self.import_item_id
        return metadata


@dataclass(frozen=True)
class NotificationEvent:
    recipient_id: str
    event_type: str
    subject_type: str
    subject_id: str
    target_url: str
    title: str
    message: str
    metadata: dict[str, object]
    actor_id: str | None = None
    dedupe_key: str = ""
