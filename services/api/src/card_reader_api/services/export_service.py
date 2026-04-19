from __future__ import annotations

from sqlmodel import Session

import card_reader_core.repositories as repositories


class ExportService:
    def export_cards_csv(
        self,
        session: Session,
        *,
        query: str | None,
        max_confidence: float | None = None,
        keyword_ids: list[str] | None = None,
        tag_ids: list[str] | None = None,
        symbol_ids: list[str] | None = None,
        type_ids: list[str] | None = None,
        mana_cost: str | None = None,
        template_id: str | None = None,
        attack_min: int | None = None,
        attack_max: int | None = None,
        health_min: int | None = None,
        health_max: int | None = None,
    ) -> str:
        return repositories.export_cards_csv(
            session,
            query=query,
            max_confidence=max_confidence,
            keyword_ids=keyword_ids,
            tag_ids=tag_ids,
            symbol_ids=symbol_ids,
            type_ids=type_ids,
            mana_cost=mana_cost,
            template_id=template_id,
            attack_min=attack_min,
            attack_max=attack_max,
            health_min=health_min,
            health_max=health_max,
        )


