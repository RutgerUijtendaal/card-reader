from __future__ import annotations

from services import CardService, ExportService, ImportService

_IMPORT_SERVICE = ImportService()
_CARD_SERVICE = CardService()
_EXPORT_SERVICE = ExportService()


def get_import_service() -> ImportService:
    return _IMPORT_SERVICE


def get_card_service() -> CardService:
    return _CARD_SERVICE


def get_export_service() -> ExportService:
    return _EXPORT_SERVICE
