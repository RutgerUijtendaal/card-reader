from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from database.connection import get_session
from services import CardService
from dependencies import get_card_service
from mappers import (
    to_card_detail_response,
    to_card_generation_response,
    to_card_summary_response,
)
from schemas import (
    CardDetailResponse,
    CardGenerationResponse,
    CardSummaryResponse,
    UpdateCardRequest,
)

router = APIRouter()


@router.get("/cards", response_model=list[CardSummaryResponse])
def list_cards(
    q: str | None = None,
    max_confidence: float | None = None,
    card_service: CardService = Depends(get_card_service),
) -> list[CardSummaryResponse]:
    with get_session() as session:
        cards = card_service.list_cards(session, query=q, max_confidence=max_confidence)
        return [to_card_summary_response(card, version) for card, version in cards]


@router.get("/cards/{card_id}", response_model=CardDetailResponse)
def get_card(card_id: str, card_service: CardService = Depends(get_card_service)) -> CardDetailResponse:
    with get_session() as session:
        card, version, image = card_service.get_card_with_image(session, card_id)
        if card is None or version is None:
            raise HTTPException(status_code=404, detail="Card not found")
        return to_card_detail_response(card, version, has_image=image is not None)


@router.patch("/cards/{card_id}", response_model=CardDetailResponse)
def patch_card(
    card_id: str,
    request: UpdateCardRequest,
    card_service: CardService = Depends(get_card_service),
) -> CardDetailResponse:
    with get_session() as session:
        updated = card_service.update_card(
            session,
            card_id=card_id,
            name=request.name,
            type_line=request.type_line,
            mana_cost=request.mana_cost,
            rules_text=request.rules_text,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Card not found")
        card, version = updated

        _, _, image = card_service.get_card_with_image(session, card.id)
        return to_card_detail_response(card, version, has_image=image is not None)


@router.get("/cards/{card_id}/generations", response_model=list[CardGenerationResponse])
def get_card_generations(
    card_id: str,
    card_service: CardService = Depends(get_card_service),
) -> list[CardGenerationResponse]:
    with get_session() as session:
        generations = card_service.list_card_generations(session, card_id)
        if not generations:
            raise HTTPException(status_code=404, detail="Card not found")
        return [to_card_generation_response(card) for card in generations]


@router.get("/cards/{card_id}/image")
def get_card_image(card_id: str, card_service: CardService = Depends(get_card_service)) -> FileResponse:
    with get_session() as session:
        card, _, image = card_service.get_card_with_image(session, card_id)
        if card is None or image is None:
            raise HTTPException(status_code=404, detail="Card image not found")

        file_path = Path(image.stored_path)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Card image file is missing")

        return FileResponse(path=file_path)

