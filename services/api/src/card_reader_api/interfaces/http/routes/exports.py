from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from card_reader_api.application.services import ExportService
from card_reader_api.infrastructure.db import get_session

router = APIRouter()
export_service = ExportService()


@router.get("/exports/csv")
def export_csv(q: str | None = None) -> StreamingResponse:
    with get_session() as session:
        csv_content = export_service.export_cards_csv(session, query=q)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cards.csv"},
    )