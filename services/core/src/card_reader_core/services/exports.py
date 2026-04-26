from __future__ import annotations

import card_reader_core.repositories as repositories


class ExportService:
    def export_cards_csv(self, **filters) -> str:
        return repositories.export_cards_csv(None, **filters)
