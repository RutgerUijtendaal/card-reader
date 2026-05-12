from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .cards import CardEditState, CardMetadata
    from .catalog import CatalogData, CatalogService
    from .imports import ImportService
    from .parser_jobs import ImportProcessorService, ItemProcessingResult, JobOptions, ParserResources
    from .templates import TemplateService

__all__ = [
    "CardEditState",
    "CardMetadata",
    "CatalogData",
    "CatalogService",
    "ImportService",
    "ImportProcessorService",
    "ItemProcessingResult",
    "JobOptions",
    "ParserResources",
    "TemplateService",
]


def __getattr__(name: str) -> Any:
    if name in {"CardEditState", "CardMetadata"}:
        from .cards import CardEditState, CardMetadata

        values = {
            "CardEditState": CardEditState,
            "CardMetadata": CardMetadata,
        }
        return values[name]
    if name in {"CatalogData", "CatalogService"}:
        from .catalog import CatalogData, CatalogService

        values = {
            "CatalogData": CatalogData,
            "CatalogService": CatalogService,
        }
        return values[name]
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
