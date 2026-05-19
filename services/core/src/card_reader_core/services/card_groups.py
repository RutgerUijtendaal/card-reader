from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from card_reader_core.models import Card, CardGroup
from card_reader_core.repositories import (
    card_group_key_exists,
    create_card_group,
    delete_card_group,
    get_card,
    get_card_group,
    get_cards,
    list_card_groups,
    list_card_groups_for_card,
    list_card_groups_for_cards,
    normalize_slug_key,
    replace_card_group_members,
    update_card_group,
)


@dataclass(frozen=True)
class CardGroupMemberInput:
    card_id: str
    position: int


class CardGroupService:
    def list_groups(self) -> list[CardGroup]:
        return list_card_groups()

    def get_group(self, group_id: str) -> CardGroup | None:
        return get_card_group(group_id)

    def get_groups_for_card(self, card_id: str) -> list[CardGroup]:
        return list_card_groups_for_card(card_id)

    def get_groups_for_cards(self, card_ids: list[str]) -> list[CardGroup]:
        return list_card_groups_for_cards(card_ids)

    @transaction.atomic
    def create_group(
        self,
        *,
        name: str | None,
        anchor_card_id: str,
        members: list[CardGroupMemberInput],
    ) -> CardGroup:
        ordered_card_ids, anchor_card, normalized_name = self._normalize_membership_payload(
            name=name,
            anchor_card_id=anchor_card_id,
            members=members,
            existing_group=None,
        )
        key = self._build_unique_key(normalized_name)
        group = create_card_group(key=key, name=normalized_name, anchor_card=anchor_card)
        replace_card_group_members(group=group, ordered_card_ids=ordered_card_ids)
        return self.get_group(group.id) or group

    @transaction.atomic
    def update_group(
        self,
        *,
        group_id: str,
        name: str | None = None,
        anchor_card_id: str | None = None,
        members: list[CardGroupMemberInput] | None = None,
    ) -> CardGroup | None:
        existing_group = self.get_group(group_id)
        if existing_group is None:
            return None

        resolved_anchor_card_id = anchor_card_id or existing_group.anchor_card_id
        resolved_name = name if name is not None else existing_group.name
        ordered_card_ids: list[str] | None = None

        if members is not None:
            ordered_card_ids, anchor_card, normalized_name = self._normalize_membership_payload(
                name=resolved_name,
                anchor_card_id=resolved_anchor_card_id,
                members=members,
                existing_group=existing_group,
            )
        else:
            anchor_card = get_card(resolved_anchor_card_id)
            if anchor_card is None:
                raise ValueError("Anchor card not found.")
            existing_member_ids = [member.card_id for member in existing_group.members.all()]
            if anchor_card.id not in existing_member_ids:
                raise ValueError("Anchor card must already be a member of the card group.")
            normalized_name = self._normalize_name(resolved_name, anchor_card)

        updates: dict[str, object] = {
            "name": normalized_name,
            "anchor_card": anchor_card,
        }
        updated = update_card_group(group_id=group_id, updates=updates)
        if updated is None:
            return None
        if ordered_card_ids is not None:
            replace_card_group_members(group=updated, ordered_card_ids=ordered_card_ids)
        return self.get_group(group_id) or updated

    def delete_group(self, *, group_id: str) -> bool:
        return delete_card_group(group_id=group_id)

    def _normalize_membership_payload(
        self,
        *,
        name: str | None,
        anchor_card_id: str,
        members: list[CardGroupMemberInput],
        existing_group: CardGroup | None,
    ) -> tuple[list[str], Card, str]:
        if len(members) < 2:
            raise ValueError("Card groups must contain at least 2 cards.")

        sorted_members = sorted(members, key=lambda row: (row.position, row.card_id))
        ordered_member_ids = [row.card_id.strip() for row in sorted_members if row.card_id.strip()]
        if len(ordered_member_ids) < 2:
            raise ValueError("Card groups must contain at least 2 cards.")
        if len(set(ordered_member_ids)) != len(ordered_member_ids):
            raise ValueError("Each card can only appear once in a card group.")
        if anchor_card_id not in ordered_member_ids:
            raise ValueError("Anchor card must be included in the card group members.")

        cards_by_id = get_cards(ordered_member_ids)
        missing_ids = [card_id for card_id in ordered_member_ids if card_id not in cards_by_id]
        if missing_ids:
            raise ValueError("One or more selected cards do not exist.")

        anchor_card = cards_by_id.get(anchor_card_id)
        if anchor_card is None:
            raise ValueError("Anchor card not found.")

        ordered_without_anchor = [card_id for card_id in ordered_member_ids if card_id != anchor_card_id]
        normalized_name = self._normalize_name(name, anchor_card)

        return [anchor_card_id, *ordered_without_anchor], anchor_card, normalized_name

    def _normalize_name(self, raw_name: str | None, anchor_card: Card) -> str:
        candidate = " ".join((raw_name or "").split()).strip() or anchor_card.label or anchor_card.key
        if not candidate:
            raise ValueError("Card group name is required.")
        return candidate

    def _build_unique_key(self, name: str) -> str:
        base_key = normalize_slug_key(name)
        if not base_key:
            raise ValueError("Card group key is invalid.")
        key = base_key
        suffix = 2
        while card_group_key_exists(key=key):
            key = f"{base_key}-{suffix}"
            suffix += 1
        return key
