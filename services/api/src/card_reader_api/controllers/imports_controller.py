import json
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from card_reader_core.database.connection import get_session
from card_reader_core.repositories import (
    SUPPORTED_IMAGE_SUFFIXES,
    fetch_items_for_job,
    fetch_job,
    list_import_jobs,
)
from card_reader_core.settings import settings
from ..services import ImportService
from ..dependencies import get_import_service
from ..mappers import to_import_job_detail_response, to_import_job_response
from ..schemas import ImportJobDetailResponse, ImportJobResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/imports", response_model=list[ImportJobResponse])
def get_imports() -> list[ImportJobResponse]:
    with get_session() as session:
        jobs = list_import_jobs(session)
        return [to_import_job_response(job) for job in jobs]


@router.post("/imports/upload", response_model=ImportJobResponse, status_code=201)
async def create_import_from_upload(
    template_id: str = Form(...),
    options_json: str = Form("{}"),
    files: list[UploadFile] = File(...),
    import_service: ImportService = Depends(get_import_service),
) -> ImportJobResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    try:
        options_raw = json.loads(options_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="options_json must be valid JSON") from exc

    if not isinstance(options_raw, dict):
        raise HTTPException(status_code=400, detail="options_json must decode to an object")

    upload_dir = settings.storage_root_dir / "uploads" / str(uuid4())
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for index, upload in enumerate(files):
        original_name = Path(upload.filename or f"upload-{index}.img").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            await upload.close()
            continue

        target_file = upload_dir / f"{index:04d}-{original_name}"
        content = await upload.read()
        target_file.write_bytes(content)
        await upload.close()
        saved_count += 1

    if saved_count == 0:
        raise HTTPException(status_code=400, detail="No supported image files found in upload")

    try:
        with get_session() as session:
            job = import_service.create_job(
                session,
                source_path=str(upload_dir),
                template_id=template_id,
                options=options_raw,
            )
            return to_import_job_response(job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to create import job from upload. template_id=%s upload_dir=%s",
            template_id,
            upload_dir,
        )
        raise HTTPException(status_code=500, detail="Failed to create import job from upload. See API logs.")


@router.get("/imports/{job_id}", response_model=ImportJobDetailResponse)
def get_import(job_id: str) -> ImportJobDetailResponse:
    with get_session() as session:
        job = fetch_job(session, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        items = fetch_items_for_job(session, job_id)
        return to_import_job_detail_response(job, items)






