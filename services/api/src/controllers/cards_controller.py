from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from database.connection import get_session
from services import CardService
from dependencies import get_card_service
from mappers import (
    to_card_detail_response,
    to_card_generation_response,
    to_metadata_option_response,
    to_card_summary_response,
)
from schemas import (
    CardFiltersResponse,
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
    keyword_ids: list[str] | None = Query(default=None),
    tag_ids: list[str] | None = Query(default=None),
    symbol_ids: list[str] | None = Query(default=None),
    type_ids: list[str] | None = Query(default=None),
    mana_cost: str | None = None,
    template_id: str | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    card_service: CardService = Depends(get_card_service),
) -> list[CardSummaryResponse]:
    with get_session() as session:
        cards = card_service.list_cards(
            session,
            query=q,
            max_confidence=max_confidence,
            keyword_ids=keyword_ids,
            tag_ids=tag_ids,
            symbol_ids=symbol_ids,
            type_ids=type_ids,
            mana_cost=mana_cost,
            template_id=template_id,
            attack_min=attack_min,
            attack_max=attack_max,
            health_min=health_min,
            health_max=health_max,
        )
        out: list[CardSummaryResponse] = []
        for card, version in cards:
            item = to_card_summary_response(card, version)
            image = card_service.get_card_image(session, version.id)
            meta = card_service.get_card_version_metadata(session, version.id)
            item.image_url = f"/cards/{card.id}/image" if image is not None else None
            item.keywords = [row.label for row in meta["keywords"]]
            item.tags = [row.label for row in meta["tags"]]
            item.symbols = [row.label for row in meta["symbols"]]
            item.types = [row.label for row in meta["types"]]
            out.append(item)
        return out


@router.get("/cards/filters", response_model=CardFiltersResponse)
def get_card_filters(card_service: CardService = Depends(get_card_service)) -> CardFiltersResponse:
    with get_session() as session:
        meta = card_service.get_filter_metadata(session)
        return CardFiltersResponse(
            keywords=[to_metadata_option_response(item) for item in meta["keywords"]],
            tags=[to_metadata_option_response(item) for item in meta["tags"]],
            symbols=[to_metadata_option_response(item) for item in meta["symbols"]],
            types=[to_metadata_option_response(item) for item in meta["types"]],
        )


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
        out: list[CardGenerationResponse] = []
        for version in generations:
            row = to_card_generation_response(version)
            image = card_service.get_card_image(session, version.id)
            meta = card_service.get_card_version_metadata(session, version.id)
            row.image_url = f"/cards/{card_id}/versions/{version.id}/image" if image is not None else None
            row.keywords = [item.label for item in meta["keywords"]]
            row.tags = [item.label for item in meta["tags"]]
            row.symbols = [item.label for item in meta["symbols"]]
            row.types = [item.label for item in meta["types"]]
            out.append(row)
        return out


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


@router.get("/cards/{card_id}/versions/{version_id}/image")
def get_card_version_image(
    card_id: str,
    version_id: str,
    card_service: CardService = Depends(get_card_service),
) -> FileResponse:
    with get_session() as session:
        card = card_service.get_card(session, card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")

        image = card_service.get_card_image(session, version_id)
        if image is None:
            raise HTTPException(status_code=404, detail="Card image not found")

        file_path = Path(image.stored_path)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Card image file is missing")
        return FileResponse(path=file_path)

