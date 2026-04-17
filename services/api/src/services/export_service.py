from __future__ import annotations

from sqlmodel import Session

import repositories as repositories


class ExportService:
    def export_cards_csv(self, session: Session, *, query: str | None) -> str:
        return repositories.export_cards_csv(session, query=query)

