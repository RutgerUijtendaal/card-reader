from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlmodel import Field, SQLModel


class ImportJobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ImportJob(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    source_path: str
    template_id: str
    options_json: str = "{}"
    status: ImportJobStatus = Field(default=ImportJobStatus.queued)
    total_items: int = 0
    processed_items: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImportJobItem(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(index=True)
    source_file: str
    status: ImportJobStatus = Field(default=ImportJobStatus.queued)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Card(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    template_id: str = Field(index=True)
    image_hash: str = Field(index=True, unique=True)
    name: str = ""
    type_line: str = ""
    mana_cost: str = ""
    rules_text: str = ""
    confidence: float = 0.0
    parse_result_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CardImage(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_id: str = Field(index=True)
    source_file: str
    stored_path: str
    width: int = 0
    height: int = 0
    checksum: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParseResult(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_id: str = Field(index=True)
    raw_ocr_json: str
    normalized_fields_json: str
    confidence_json: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Tag(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)


class CardTag(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_id: str = Field(index=True)
    tag_id: str = Field(index=True)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_json_field(value: str) -> dict[str, Any]:
    import json

    return json.loads(value) if value else {}