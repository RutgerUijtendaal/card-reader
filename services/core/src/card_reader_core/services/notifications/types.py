from __future__ import annotations

from dataclasses import dataclass


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
