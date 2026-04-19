from __future__ import annotations

from services import (
    CardService,
    CatalogService,
    ExportService,
    ImportService,
    MaintenanceService,
    TemplateService,
)

_IMPORT_SERVICE = ImportService()
_CARD_SERVICE = CardService()
_EXPORT_SERVICE = ExportService()
_MAINTENANCE_SERVICE = MaintenanceService()
_CATALOG_SERVICE = CatalogService()
_TEMPLATE_SERVICE = TemplateService()


def get_import_service() -> ImportService:
    return _IMPORT_SERVICE


def get_card_service() -> CardService:
    return _CARD_SERVICE


def get_export_service() -> ExportService:
    return _EXPORT_SERVICE


def get_maintenance_service() -> MaintenanceService:
    return _MAINTENANCE_SERVICE


def get_catalog_service() -> CatalogService:
    return _CATALOG_SERVICE


def get_template_service() -> TemplateService:
    return _TEMPLATE_SERVICE
