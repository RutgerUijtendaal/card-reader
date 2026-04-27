from __future__ import annotations

from typing import Any

import card_reader_core.repositories as repositories


class ExportService:
    def export_cards_csv(self, **filters: Any) -> str:
        return repositories.export_cards_csv(**filters)
