from pathlib import Path

from fastapi import APIRouter, HTTPException

from card_reader_api.application.services import ImportService
from card_reader_api.infrastructure.db import get_session
from card_reader_api.infrastructure.parser import CardParser
from card_reader_api.infrastructure.repositories import fetch_items_for_job, fetch_job, list_import_jobs
from card_reader_api.interfaces.http.schemas import CreateImportJobRequest, ImportJobResponse

router = APIRouter()
import_service = ImportService(parser=CardParser(Path(__file__).resolve().parents[3] / "infrastructure" / "templates"))


@router.get("/imports", response_model=list[ImportJobResponse])
def get_imports() -> list[ImportJobResponse]:
    with get_session() as session:
        jobs = list_import_jobs(session)
        return [
            ImportJobResponse(
                id=job.id,
                source_path=job.source_path,
                template_id=job.template_id,
                status=job.status,
                total_items=job.total_items,
                processed_items=job.processed_items,
            )
            for job in jobs
        ]


@router.post("/imports", response_model=ImportJobResponse, status_code=201)
def create_import(request: CreateImportJobRequest) -> ImportJobResponse:
    source_path = Path(request.source_path)
    if not source_path.exists() or not source_path.is_dir():
        raise HTTPException(status_code=400, detail="source_path must point to an existing directory")

    with get_session() as session:
        job = import_service.create_job(
            session,
            source_path=request.source_path,
            template_id=request.template_id,
            options=request.options,
        )
        return ImportJobResponse(
            id=job.id,
            source_path=job.source_path,
            template_id=job.template_id,
            status=job.status,
            total_items=job.total_items,
            processed_items=job.processed_items,
        )


@router.get("/imports/{job_id}")
def get_import(job_id: str) -> dict[str, object]:
    with get_session() as session:
        job = fetch_job(session, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        items = fetch_items_for_job(session, job_id)
        return {
            "id": job.id,
            "source_path": job.source_path,
            "template_id": job.template_id,
            "status": job.status,
            "total_items": job.total_items,
            "processed_items": job.processed_items,
            "items": [
                {
                    "id": item.id,
                    "source_file": item.source_file,
                    "status": item.status,
                    "error_message": item.error_message,
                }
                for item in items
            ],
        }
