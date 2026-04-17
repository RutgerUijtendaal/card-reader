from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from .base import now_utc


class CardVersion(SQLModel, table=True):
    __tablename__ = "card_version"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_id: str = Field(index=True)
    version_number: int = Field(default=1, index=True)
    template_id: str = Field(index=True)
    image_hash: str = Field(index=True)
    name: str = ""
    type_line: str = ""
    mana_cost: str = ""
    mana_symbols_json: str = "[]"
    attack: int | None = None
    health: int | None = None
    rules_text: str = ""
    confidence: float = 0.0
    parse_result_id: str | None = Field(default=None, index=True)
    is_latest: bool = Field(default=True, index=True)
    previous_version_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CardVersionImage(SQLModel, table=True):
    __tablename__ = "card_version_image"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_version_id: str = Field(index=True)
    source_file: str
    stored_path: str
    width: int = 0
    height: int = 0
    checksum: str = Field(index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class ParseResult(SQLModel, table=True):
    __tablename__ = "parse_result"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_version_id: str = Field(index=True)
    raw_ocr_json: str
    normalized_fields_json: str
    confidence_json: str
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


