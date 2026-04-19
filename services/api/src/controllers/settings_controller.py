import logging
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from database.connection import get_session
from dependencies import get_catalog_service, get_maintenance_service, get_template_service
from models import Keyword, Symbol, Tag, Template, Type
from settings import settings
from schemas import (
    CatalogResponse,
    ClearStorageRequest,
    KeywordResponse,
    OpenStorageLocationResponse,
    KeywordUpsertRequest,
    MaintenanceActionResponse,
    SymbolResponse,
    SymbolAssetUploadResponse,
    SymbolUpsertRequest,
    TemplateResponse,
    TemplateUpsertRequest,
    TagResponse,
    TagUpsertRequest,
    TypeResponse,
    TypeUpsertRequest,
)
from services import CatalogService, MaintenanceService, TemplateService

router = APIRouter()
logger = logging.getLogger(__name__)
_ALLOWED_SYMBOL_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


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


@router.post("/settings/maintenance/open-storage-location", response_model=OpenStorageLocationResponse)
def open_storage_location(
    maintenance_service: MaintenanceService = Depends(get_maintenance_service),
) -> OpenStorageLocationResponse:
    try:
        result = maintenance_service.open_storage_location()
    except Exception:
        logger.exception("Maintenance open-storage-location failed")
        raise HTTPException(status_code=500, detail="Failed to open storage location.") from None
    return OpenStorageLocationResponse(message=result.message, path=result.path)


@router.get("/settings/catalog", response_model=CatalogResponse)
def get_catalog(
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> CatalogResponse:
    with get_session() as session:
        data = catalog_service.list_catalog(session)

    return CatalogResponse(
        keywords=[_to_keyword_response(item) for item in data["keywords"]],
        tags=[_to_tag_response(item) for item in data["tags"]],
        symbols=[_to_symbol_response(item) for item in data["symbols"]],
        types=[_to_type_response(item) for item in data["types"]],
    )


@router.get("/settings/templates", response_model=list[TemplateResponse])
def get_templates(
    template_service: TemplateService = Depends(get_template_service),
) -> list[TemplateResponse]:
    with get_session() as session:
        templates = template_service.list_templates(session)
    return [_to_template_response(item) for item in templates]


@router.post("/settings/templates", response_model=TemplateResponse)
def create_template(
    request: TemplateUpsertRequest,
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    _require_label(request.label)
    definition_json = request.definition_json
    if definition_json is None:
        raise HTTPException(status_code=400, detail="definition_json is required")

    with get_session() as session:
        try:
            item = template_service.create_template(
                session,
                label=request.label or "",
                key=request.key,
                definition_json=definition_json,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Create template failed")
            raise HTTPException(status_code=500, detail="Failed to create template.") from None
    return _to_template_response(item)


@router.patch("/settings/templates/{entry_id}", response_model=TemplateResponse)
def update_template(
    entry_id: str,
    request: TemplateUpsertRequest,
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    with get_session() as session:
        try:
            item = template_service.update_template(
                session,
                entry_id=entry_id,
                label=request.label,
                key=request.key,
                definition_json=request.definition_json,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Update template failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to update template.") from None
        if item is None:
            raise HTTPException(status_code=404, detail="Template not found")
    return _to_template_response(item)


@router.delete("/settings/templates/{entry_id}", status_code=204)
def delete_template(
    entry_id: str,
    template_service: TemplateService = Depends(get_template_service),
) -> None:
    with get_session() as session:
        try:
            deleted = template_service.delete_template(session, entry_id=entry_id)
        except Exception:
            logger.exception("Delete template failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to delete template.") from None
        if not deleted:
            raise HTTPException(status_code=404, detail="Template not found")


@router.post("/settings/keywords", response_model=KeywordResponse)
def create_keyword(
    request: KeywordUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> KeywordResponse:
    _require_label(request.label)
    with get_session() as session:
        try:
            item = catalog_service.create_keyword(session, label=request.label, key=request.key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Create keyword failed")
            raise HTTPException(status_code=500, detail="Failed to create keyword.") from None
    return _to_keyword_response(item)


@router.patch("/settings/keywords/{entry_id}", response_model=KeywordResponse)
def update_keyword(
    entry_id: str,
    request: KeywordUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> KeywordResponse:
    with get_session() as session:
        try:
            item = catalog_service.update_keyword(
                session,
                entry_id=entry_id,
                label=request.label,
                key=request.key,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Update keyword failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to update keyword.") from None
        if item is None:
            raise HTTPException(status_code=404, detail="Keyword not found")
    return _to_keyword_response(item)


@router.delete("/settings/keywords/{entry_id}", status_code=204)
def delete_keyword(
    entry_id: str,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> None:
    with get_session() as session:
        try:
            deleted = catalog_service.delete_keyword(session, entry_id=entry_id)
        except Exception:
            logger.exception("Delete keyword failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to delete keyword.") from None
        if not deleted:
            raise HTTPException(status_code=404, detail="Keyword not found")


@router.post("/settings/tags", response_model=TagResponse)
def create_tag(
    request: TagUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> TagResponse:
    _require_label(request.label)
    with get_session() as session:
        try:
            item = catalog_service.create_tag(session, label=request.label, key=request.key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Create tag failed")
            raise HTTPException(status_code=500, detail="Failed to create tag.") from None
    return _to_tag_response(item)


@router.patch("/settings/tags/{entry_id}", response_model=TagResponse)
def update_tag(
    entry_id: str,
    request: TagUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> TagResponse:
    with get_session() as session:
        try:
            item = catalog_service.update_tag(
                session,
                entry_id=entry_id,
                label=request.label,
                key=request.key,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Update tag failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to update tag.") from None
        if item is None:
            raise HTTPException(status_code=404, detail="Tag not found")
    return _to_tag_response(item)


@router.delete("/settings/tags/{entry_id}", status_code=204)
def delete_tag(
    entry_id: str,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> None:
    with get_session() as session:
        try:
            deleted = catalog_service.delete_tag(session, entry_id=entry_id)
        except Exception:
            logger.exception("Delete tag failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to delete tag.") from None
        if not deleted:
            raise HTTPException(status_code=404, detail="Tag not found")


@router.post("/settings/types", response_model=TypeResponse)
def create_type(
    request: TypeUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> TypeResponse:
    _require_label(request.label)
    with get_session() as session:
        try:
            item = catalog_service.create_type(session, label=request.label, key=request.key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Create type failed")
            raise HTTPException(status_code=500, detail="Failed to create type.") from None
    return _to_type_response(item)


@router.patch("/settings/types/{entry_id}", response_model=TypeResponse)
def update_type(
    entry_id: str,
    request: TypeUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> TypeResponse:
    with get_session() as session:
        try:
            item = catalog_service.update_type(
                session,
                entry_id=entry_id,
                label=request.label,
                key=request.key,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Update type failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to update type.") from None
        if item is None:
            raise HTTPException(status_code=404, detail="Type not found")
    return _to_type_response(item)


@router.delete("/settings/types/{entry_id}", status_code=204)
def delete_type(
    entry_id: str,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> None:
    with get_session() as session:
        try:
            deleted = catalog_service.delete_type(session, entry_id=entry_id)
        except Exception:
            logger.exception("Delete type failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to delete type.") from None
        if not deleted:
            raise HTTPException(status_code=404, detail="Type not found")


@router.post("/settings/symbols", response_model=SymbolResponse)
def create_symbol(
    request: SymbolUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> SymbolResponse:
    _require_label(request.label)
    with get_session() as session:
        try:
            item = catalog_service.create_symbol(
                session,
                label=request.label,
                key=request.key,
                symbol_type=request.symbol_type,
                detector_type=request.detector_type,
                detection_config_json=request.detection_config_json,
                reference_assets_json=request.reference_assets_json,
                text_token=request.text_token,
                enabled=request.enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Create symbol failed")
            raise HTTPException(status_code=500, detail="Failed to create symbol.") from None
    return _to_symbol_response(item)


@router.post("/settings/symbols/assets/upload", response_model=SymbolAssetUploadResponse)
async def upload_symbol_asset(file: UploadFile = File(...)) -> SymbolAssetUploadResponse:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_SYMBOL_ASSET_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported symbol asset file type. Use png/jpg/jpeg/webp/bmp/tif/tiff.",
        )

    symbols_dir = settings.storage_root_dir / "symbols"
    symbols_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(filename).stem.strip().lower()
    safe_stem = re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-") or "symbol"
    stored_name = f"{safe_stem}-{uuid4().hex[:8]}{suffix}"
    target_path = symbols_dir / stored_name

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        target_path.write_bytes(content)
    except Exception:
        logger.exception("Failed to store symbol asset upload. filename=%s", filename)
        raise HTTPException(status_code=500, detail="Failed to store symbol asset.") from None
    finally:
        await file.close()

    return SymbolAssetUploadResponse(
        relative_path=str(Path("symbols") / stored_name).replace("\\", "/"),
        absolute_path=str(target_path),
    )


@router.delete("/settings/symbols/{entry_id}", status_code=204)
def delete_symbol(
    entry_id: str,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> None:
    with get_session() as session:
        try:
            deleted = catalog_service.delete_symbol(session, entry_id=entry_id)
        except Exception:
            logger.exception("Delete symbol failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to delete symbol.") from None
        if not deleted:
            raise HTTPException(status_code=404, detail="Symbol not found")


@router.patch("/settings/symbols/{entry_id}", response_model=SymbolResponse)
def update_symbol(
    entry_id: str,
    request: SymbolUpsertRequest,
    catalog_service: CatalogService = Depends(get_catalog_service),
) -> SymbolResponse:
    with get_session() as session:
        try:
            item = catalog_service.update_symbol(
                session,
                entry_id=entry_id,
                label=request.label,
                key=request.key,
                symbol_type=request.symbol_type,
                detector_type=request.detector_type,
                detection_config_json=request.detection_config_json,
                reference_assets_json=request.reference_assets_json,
                text_token=request.text_token,
                enabled=request.enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except Exception:
            logger.exception("Update symbol failed. entry_id=%s", entry_id)
            raise HTTPException(status_code=500, detail="Failed to update symbol.") from None
        if item is None:
            raise HTTPException(status_code=404, detail="Symbol not found")
    return _to_symbol_response(item)


def _require_label(label: str | None) -> str:
    if label is None:
        raise HTTPException(status_code=400, detail="label is required")
    return label


def _to_keyword_response(item: Keyword) -> KeywordResponse:
    return KeywordResponse(id=item.id, key=item.key, label=item.label)


def _to_tag_response(item: Tag) -> TagResponse:
    return TagResponse(id=item.id, key=item.key, label=item.label)


def _to_type_response(item: Type) -> TypeResponse:
    return TypeResponse(id=item.id, key=item.key, label=item.label)


def _to_symbol_response(item: Symbol) -> SymbolResponse:
    return SymbolResponse(
        id=item.id,
        key=item.key,
        label=item.label,
        symbol_type=item.symbol_type,
        detector_type=item.detector_type,
        detection_config_json=item.detection_config_json,
        reference_assets_json=item.reference_assets_json,
        text_token=item.text_token,
        enabled=item.enabled,
    )


def _to_template_response(item: Template) -> TemplateResponse:
    return TemplateResponse(
        id=item.id,
        key=item.key,
        label=item.label,
        definition_json=item.definition_json,
    )
