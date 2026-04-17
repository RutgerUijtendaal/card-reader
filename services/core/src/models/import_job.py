from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlmodel import Field, SQLModel

from .base import now_utc


class ImportJobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ImportJob(SQLModel, table=True):
    __tablename__ = "import_job"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    source_path: str
    template_id: str
    options_json: str = "{}"
    status: ImportJobStatus = Field(default=ImportJobStatus.queued)
    total_items: int = 0
    processed_items: int = 0
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class ImportJobItem(SQLModel, table=True):
    __tablename__ = "import_job_item"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(index=True)
    source_file: str
    status: ImportJobStatus = Field(default=ImportJobStatus.queued)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


