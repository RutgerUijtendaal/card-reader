from pydantic import BaseModel


class ImportJobResponse(BaseModel):
    id: str
    source_path: str
    template_id: str
    status: str
    total_items: int
    processed_items: int


class ImportJobItemResponse(BaseModel):
    id: str
    source_file: str
    status: str
    error_message: str | None = None


class ImportJobDetailResponse(BaseModel):
    id: str
    source_path: str
    template_id: str
    status: str
    total_items: int
    processed_items: int
    items: list[ImportJobItemResponse]


class CardSummaryResponse(BaseModel):
    id: str
    key: str
    label: str
    name: str
    template_id: str
    version_id: str
    version_number: int
    is_latest: bool
    type_line: str
    mana_cost: str
    mana_symbols: list[str] = []
    attack: int | None = None
    health: int | None = None
    confidence: float
    image_url: str | None = None
    keywords: list[str] = []
    tags: list[str] = []
    symbols: list[str] = []
    types: list[str] = []


class CardDetailResponse(BaseModel):
    id: str
    key: str
    label: str
    version_id: str
    version_number: int
    name: str
    previous_version_id: str | None = None
    is_latest: bool
    type_line: str
    mana_cost: str
    mana_symbols: list[str] = []
    attack: int | None = None
    health: int | None = None
    rules_text: str
    confidence: float
    image_url: str | None = None


class CardGenerationResponse(BaseModel):
    id: str
    version_number: int
    name: str
    type_line: str
    mana_cost: str
    mana_symbols: list[str] = []
    attack: int | None = None
    health: int | None = None
    rules_text: str
    confidence: float
    created_at: str
    image_url: str | None = None
    keywords: list[str] = []
    tags: list[str] = []
    symbols: list[str] = []
    types: list[str] = []


class MetadataOptionResponse(BaseModel):
    id: str
    key: str
    label: str


class SymbolFilterOptionResponse(MetadataOptionResponse):
    text_token: str = ""
    asset_url: str | None = None


class CardFiltersResponse(BaseModel):
    keywords: list[MetadataOptionResponse] = []
    tags: list[MetadataOptionResponse] = []
    symbols: list[SymbolFilterOptionResponse] = []
    types: list[MetadataOptionResponse] = []


class MaintenanceActionResponse(BaseModel):
    message: str
    removed_paths: list[str] = []


class OpenStorageLocationResponse(BaseModel):
    message: str
    path: str


class KeywordResponse(BaseModel):
    id: str
    key: str
    label: str


class TagResponse(BaseModel):
    id: str
    key: str
    label: str


class TypeResponse(BaseModel):
    id: str
    key: str
    label: str


class SymbolResponse(BaseModel):
    id: str
    key: str
    label: str
    symbol_type: str
    detector_type: str
    detection_config_json: str
    reference_assets_json: str
    text_token: str
    enabled: bool


class SymbolAssetUploadResponse(BaseModel):
    relative_path: str
    absolute_path: str


class TemplateResponse(BaseModel):
    id: str
    key: str
    label: str
    definition_json: str


class CatalogResponse(BaseModel):
    keywords: list[KeywordResponse] = []
    tags: list[TagResponse] = []
    symbols: list[SymbolResponse] = []
    types: list[TypeResponse] = []
