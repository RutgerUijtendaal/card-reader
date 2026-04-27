from __future__ import annotations

from typing import Any, TypedDict

import card_reader_core.repositories as repositories
from card_reader_core.models import Card, CardVersion, CardVersionImage, Keyword, Symbol, Tag, Type


class CardMetadata(TypedDict):
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


class CardService:
    def list_cards(self, **filters: Any) -> list[tuple[Card, CardVersion]]:
        return repositories.list_cards(**filters)

    def list_card_generations(self, card_id: str) -> list[CardVersion]:
        return repositories.list_card_generations(card_id)

    def get_filter_metadata(self) -> CardMetadata:
        return {
            "keywords": repositories.list_keywords(),
            "tags": repositories.list_tags(),
            "symbols": repositories.list_symbols(),
            "types": repositories.list_types(),
        }

    def get_card_with_image(
        self,
        card_id: str,
    ) -> tuple[Card | None, CardVersion | None, CardVersionImage | None]:
        card = repositories.get_card(card_id)
        if card is None:
            return None, None, None
        version = repositories.get_latest_card_version(card_id)
        if version is None:
            return card, None, None
        image = repositories.get_card_image(version.id)
        return card, version, image

    def get_card(self, card_id: str) -> Card | None:
        return repositories.get_card(card_id)

    def get_card_image(self, card_version_id: str) -> CardVersionImage | None:
        return repositories.get_card_image(card_version_id)

    def get_card_version_metadata(self, card_version_id: str) -> CardMetadata:
        return {
            "keywords": repositories.get_keywords_for_card_version(card_version_id),
            "tags": repositories.get_tags_for_card_version(card_version_id),
            "symbols": repositories.get_symbols_for_card_version(card_version_id),
            "types": repositories.get_types_for_card_version(card_version_id),
        }

    def update_card(
        self,
        *,
        card_id: str,
        name: str | None,
        type_line: str | None,
        mana_cost: str | None,
        rules_text: str | None,
    ) -> tuple[Card, CardVersion] | None:
        return repositories.update_card(
            card_id=card_id,
            name=name,
            type_line=type_line,
            mana_cost=mana_cost,
            rules_text=rules_text,
        )
