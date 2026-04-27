from __future__ import annotations

from typing import Any

from card_reader_core.repositories.exports_repository import export_cards_csv


class ExportService:
    def export_cards_csv(self, **filters: Any) -> str:
        return export_cards_csv(**filters)
