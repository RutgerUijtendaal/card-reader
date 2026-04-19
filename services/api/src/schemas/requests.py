from pydantic import BaseModel
from typing import Literal


class ClearStorageRequest(BaseModel):
    include_images: bool = True


class KeywordUpsertRequest(BaseModel):
    label: str | None = None
    key: str | None = None


class TagUpsertRequest(BaseModel):
    label: str | None = None
    key: str | None = None


class TypeUpsertRequest(BaseModel):
    label: str | None = None
    key: str | None = None


class SymbolUpsertRequest(BaseModel):
    label: str | None = None
    key: str | None = None
    symbol_type: str | None = None
    detector_type: Literal["template"] | None = None
    detection_config_json: str | None = None
    reference_assets_json: str | None = None
    text_token: str | None = None
    enabled: bool | None = None


class TemplateUpsertRequest(BaseModel):
    label: str | None = None
    key: str | None = None
    definition_json: str | None = None
