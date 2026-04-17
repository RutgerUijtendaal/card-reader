from pydantic import BaseModel, Field


class CreateImportJobRequest(BaseModel):
    source_path: str
    template_id: str
    options: dict[str, object] = Field(default_factory=dict)


class ImportJobResponse(BaseModel):
    id: str
    source_path: str
    template_id: str
    status: str
    total_items: int
    processed_items: int


class CardSummaryResponse(BaseModel):
    id: str
    name: str
    template_id: str
    confidence: float


class CardDetailResponse(BaseModel):
    id: str
    name: str
    type_line: str
    mana_cost: str
    rules_text: str
    confidence: float
    image_path: str | None = None


class UpdateCardRequest(BaseModel):
    name: str | None = None
    type_line: str | None = None
    mana_cost: str | None = None
    rules_text: str | None = None