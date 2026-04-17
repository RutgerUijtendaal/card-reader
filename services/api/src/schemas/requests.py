from pydantic import BaseModel


class UpdateCardRequest(BaseModel):
    name: str | None = None
    type_line: str | None = None
    mana_cost: str | None = None
    rules_text: str | None = None
