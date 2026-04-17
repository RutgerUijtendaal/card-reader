from __future__ import annotations

from sqlmodel import Session

import repositories as repositories


class CardService:
    def list_cards(self, session: Session, *, query: str | None, max_confidence: float | None):
        return repositories.list_cards(session, query=query, max_confidence=max_confidence)

    def list_card_generations(self, session: Session, card_id: str):
        return repositories.list_card_generations(session, card_id)

    def get_card_with_image(self, session: Session, card_id: str):
        card = repositories.get_card(session, card_id)
        if card is None:
            return None, None, None
        version = repositories.get_latest_card_version(session, card_id)
        if version is None:
            return card, None, None
        image = repositories.get_card_image(session, version.id)
        return card, version, image

    def update_card(
        self,
        session: Session,
        *,
        card_id: str,
        name: str | None,
        type_line: str | None,
        mana_cost: str | None,
        rules_text: str | None,
    ):
        return repositories.update_card(
            session,
            card_id=card_id,
            name=name,
            type_line=type_line,
            mana_cost=mana_cost,
            rules_text=rules_text,
        )

