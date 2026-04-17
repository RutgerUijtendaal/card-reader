from __future__ import annotations

from sqlmodel import Session

import repositories as repositories


class CardService:
    def list_cards(
        self,
        session: Session,
        *,
        query: str | None,
        max_confidence: float | None,
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
    ):
        return repositories.list_cards(
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

    def list_card_generations(self, session: Session, card_id: str):
        return repositories.list_card_generations(session, card_id)

    def get_filter_metadata(self, session: Session):
        return {
            "keywords": repositories.list_keywords(session),
            "tags": repositories.list_tags(session),
            "symbols": repositories.list_symbols(session),
            "types": repositories.list_types(session),
        }

    def get_card_with_image(self, session: Session, card_id: str):
        card = repositories.get_card(session, card_id)
        if card is None:
            return None, None, None
        version = repositories.get_latest_card_version(session, card_id)
        if version is None:
            return card, None, None
        image = repositories.get_card_image(session, version.id)
        return card, version, image

    def get_card(self, session: Session, card_id: str):
        return repositories.get_card(session, card_id)

    def get_card_image(self, session: Session, card_version_id: str):
        return repositories.get_card_image(session, card_version_id)

    def get_card_version_metadata(self, session: Session, card_version_id: str):
        return {
            "keywords": repositories.get_keywords_for_card_version(session, card_version_id),
            "tags": repositories.get_tags_for_card_version(session, card_version_id),
            "symbols": repositories.get_symbols_for_card_version(session, card_version_id),
            "types": repositories.get_types_for_card_version(session, card_version_id),
        }

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

