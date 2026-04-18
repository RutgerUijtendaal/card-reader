import logging

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_maintenance_service
from schemas import ClearStorageRequest, MaintenanceActionResponse
from services import MaintenanceService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/settings/maintenance/rebuild-database", response_model=MaintenanceActionResponse)
def rebuild_database(
    maintenance_service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceActionResponse:
    try:
        result = maintenance_service.rebuild_database()
    except Exception:
        logger.exception("Maintenance rebuild-database failed")
        raise HTTPException(status_code=500, detail="Failed to rebuild database.") from None
    return MaintenanceActionResponse(message=result.message, removed_paths=result.removed_paths)


@router.post("/settings/maintenance/clear-storage", response_model=MaintenanceActionResponse)
def clear_storage(
    request: ClearStorageRequest,
    maintenance_service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceActionResponse:
    try:
        result = maintenance_service.clear_storage_data(include_images=request.include_images)
    except Exception:
        logger.exception("Maintenance clear-storage failed. include_images=%s", request.include_images)
        raise HTTPException(status_code=500, detail="Failed to clear storage data.") from None
    return MaintenanceActionResponse(message=result.message, removed_paths=result.removed_paths)
