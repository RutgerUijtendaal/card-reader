from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from database.connection import get_session
from services import ExportService
from dependencies import get_export_service

router = APIRouter()


@router.get("/exports/csv")
def export_csv(
    q: str | None = None,
    export_service: ExportService = Depends(get_export_service),
) -> StreamingResponse:
    with get_session() as session:
        csv_content = export_service.export_cards_csv(session, query=q)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cards.csv"},
    )

