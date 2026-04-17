from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from .base import now_utc


class Card(SQLModel, table=True):
    __tablename__ = "card"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    key: str = Field(default="", index=True, unique=True)
    label: str = ""
    latest_version_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


