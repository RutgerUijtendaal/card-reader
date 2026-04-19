from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from .base import now_utc


class Tag(SQLModel, table=True):
    __tablename__ = "tag"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    key: str = Field(default="", index=True, unique=True)
    label: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Symbol(SQLModel, table=True):
    __tablename__ = "symbol"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    key: str = Field(default="", index=True, unique=True)
    label: str = ""
    symbol_type: str = Field(default="generic", index=True)
    detector_type: str = Field(default="template", index=True)
    detection_config_json: str = "{}"
    reference_assets_json: str = "[]"
    text_token: str = ""
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Keyword(SQLModel, table=True):
    __tablename__ = "keyword"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    key: str = Field(default="", index=True, unique=True)
    label: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Type(SQLModel, table=True):
    __tablename__ = "type"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    key: str = Field(default="", index=True, unique=True)
    label: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CardVersionTag(SQLModel, table=True):
    __tablename__ = "card_version_tag"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_version_id: str = Field(index=True)
    tag_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CardVersionSymbol(SQLModel, table=True):
    __tablename__ = "card_version_symbol"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_version_id: str = Field(index=True)
    symbol_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CardVersionKeyword(SQLModel, table=True):
    __tablename__ = "card_version_keyword"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_version_id: str = Field(index=True)
    keyword_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CardVersionType(SQLModel, table=True):
    __tablename__ = "card_version_type"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    card_version_id: str = Field(index=True)
    type_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


