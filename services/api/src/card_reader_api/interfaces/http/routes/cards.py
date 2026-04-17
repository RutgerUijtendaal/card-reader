from fastapi import APIRouter, HTTPException

from card_reader_api.application.services import CardService
from card_reader_api.infrastructure.db import get_session
from card_reader_api.interfaces.http.schemas import CardDetailResponse, CardSummaryResponse, UpdateCardRequest

router = APIRouter()
card_service = CardService()


@router.get("/cards", response_model=list[CardSummaryResponse])
def list_cards(q: str | None = None, max_confidence: float | None = None) -> list[CardSummaryResponse]:
    with get_session() as session:
        cards = card_service.list_cards(session, query=q, max_confidence=max_confidence)
        return [
            CardSummaryResponse(
                id=card.id,
                name=card.name,
                template_id=card.template_id,
                confidence=card.confidence,
            )
            for card in cards
        ]


@router.get("/cards/{card_id}", response_model=CardDetailResponse)
def get_card(card_id: str) -> CardDetailResponse:
    with get_session() as session:
        card, image = card_service.get_card_with_image(session, card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")
        return CardDetailResponse(
            id=card.id,
            name=card.name,
            type_line=card.type_line,
            mana_cost=card.mana_cost,
            rules_text=card.rules_text,
            confidence=card.confidence,
            image_path=image.stored_path if image else None,
        )


@router.patch("/cards/{card_id}", response_model=CardDetailResponse)
def patch_card(card_id: str, request: UpdateCardRequest) -> CardDetailResponse:
    with get_session() as session:
        card = card_service.update_card(
            session,
            card_id=card_id,
            name=request.name,
            type_line=request.type_line,
            mana_cost=request.mana_cost,
            rules_text=request.rules_text,
        )
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")

        _, image = card_service.get_card_with_image(session, card.id)
        return CardDetailResponse(
            id=card.id,
            name=card.name,
            type_line=card.type_line,
            mana_cost=card.mana_cost,
            rules_text=card.rules_text,
            confidence=card.confidence,
            image_path=image.stored_path if image else None,
        )