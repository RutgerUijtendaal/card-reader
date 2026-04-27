from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .cards import CardMetadata, CardService
    from .catalog import CatalogData, CatalogService
    from .exports import ExportService
    from .imports import ImportService
    from .parser_jobs import ImportProcessorService, ItemProcessingResult, JobOptions, ParserResources
    from .templates import TemplateService

__all__ = [
    "CardMetadata",
    "CardService",
    "CatalogData",
    "CatalogService",
    "ExportService",
    "ImportService",
    "ImportProcessorService",
    "ItemProcessingResult",
    "JobOptions",
    "ParserResources",
    "TemplateService",
]


def __getattr__(name: str) -> Any:
    if name in {"CardMetadata", "CardService"}:
        from .cards import CardMetadata, CardService

        values = {
            "CardMetadata": CardMetadata,
            "CardService": CardService,
        }
        return values[name]
    if name in {"CatalogData", "CatalogService"}:
        from .catalog import CatalogData, CatalogService

        values = {
            "CatalogData": CatalogData,
            "CatalogService": CatalogService,
        }
        return values[name]
    if name == "ExportService":
        from .exports import ExportService

        return ExportService
    if name == "ImportService":
        from .imports import ImportService

        return ImportService
    if name in {
        "ImportProcessorService",
        "ItemProcessingResult",
        "JobOptions",
        "ParserResources",
    }:
        from .parser_jobs import (
            ImportProcessorService,
            ItemProcessingResult,
            JobOptions,
            ParserResources,
        )

        values = {
            "ImportProcessorService": ImportProcessorService,
            "ItemProcessingResult": ItemProcessingResult,
            "JobOptions": JobOptions,
            "ParserResources": ParserResources,
        }
        return values[name]
    if name == "TemplateService":
        from .templates import TemplateService

        return TemplateService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
