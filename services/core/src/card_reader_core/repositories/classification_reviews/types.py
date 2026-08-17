from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from card_reader_core.models import CardClassificationReviewItem

ClassificationReviewStatus = Literal["open", "resolved", "dismissed"]
ClassificationReviewStatusFilter = ClassificationReviewStatus | Literal["all"]
CLASSIFICATION_REVIEW_OPEN_STATUS: ClassificationReviewStatus = "open"


@dataclass(frozen=True)
class PaginatedClassificationReviewItems:
    count: int
    page: int
    page_size: int
    results: list[CardClassificationReviewItem]
