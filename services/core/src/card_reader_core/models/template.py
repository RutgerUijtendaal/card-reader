from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from .base import now_utc


class Template(SQLModel, table=True):
    __tablename__ = "template"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    key: str = Field(default="", index=True, unique=True)
    label: str = ""
    definition_json: str = "{}"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
