from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

# Import model modules eagerly so Django registers every model class when the
# app loads. The lazy export mechanism below is fine for attribute access, but
# not sufficient for ORM relation resolution across modules.
from . import card as _card_module
from . import card_version as _card_version_module
from . import import_job as _import_job_module
from . import metadata as _metadata_module
from . import template as _template_module

if TYPE_CHECKING:
    from .base import now_utc
    from .card import Card
    from .card_version import CardVersion, CardVersionImage, ParseResult
    from .import_job import ImportJob, ImportJobItem, ImportJobStatus
    from .metadata import (
        CardVersionKeyword,
        CardVersionSymbol,
        CardVersionTag,
        CardVersionType,
        Keyword,
        Symbol,
        Tag,
        Type,
    )
    from .template import Template

_EXPORTS = {
    "now_utc": ".base",
    "ImportJobStatus": ".import_job",
    "ImportJob": ".import_job",
    "ImportJobItem": ".import_job",
    "Card": ".card",
    "CardVersion": ".card_version",
    "CardVersionImage": ".card_version",
    "ParseResult": ".card_version",
    "Tag": ".metadata",
    "Symbol": ".metadata",
    "Keyword": ".metadata",
    "Type": ".metadata",
    "CardVersionTag": ".metadata",
    "CardVersionSymbol": ".metadata",
    "CardVersionKeyword": ".metadata",
    "CardVersionType": ".metadata",
    "Template": ".template",
}

__all__ = [
    "now_utc",
    "ImportJobStatus",
    "ImportJob",
    "ImportJobItem",
    "Card",
    "CardVersion",
    "CardVersionImage",
    "ParseResult",
    "Tag",
    "Symbol",
    "Keyword",
    "Type",
    "CardVersionTag",
    "CardVersionSymbol",
    "CardVersionKeyword",
    "CardVersionType",
    "Template",
]


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
