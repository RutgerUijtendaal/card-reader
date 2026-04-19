import logging

from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from card_reader_core.database.connection import get_session
from ..services import ExportService
from ..dependencies import get_export_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/exports/csv")
def export_csv(
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
    export_service: ExportService = Depends(get_export_service),
) -> StreamingResponse:
    try:
        with get_session() as session:
            csv_content = export_service.export_cards_csv(
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
    except Exception:
        logger.exception(
            "CSV export failed. q=%s max_confidence=%s template_id=%s mana_cost=%s "
            "attack_min=%s attack_max=%s health_min=%s health_max=%s "
            "keyword_ids=%s tag_ids=%s symbol_ids=%s type_ids=%s",
            q,
            max_confidence,
            template_id,
            mana_cost,
            attack_min,
            attack_max,
            health_min,
            health_max,
            keyword_ids,
            tag_ids,
            symbol_ids,
            type_ids,
        )
        raise HTTPException(status_code=500, detail="CSV export failed. Check API logs.") from None

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cards.csv"},
    )




