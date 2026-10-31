from __future__ import annotations

from typing import Any
from uuid import UUID

from card_reader_core.markup import render_markup_plain
from card_reader_core.models import CARD_FACTIONS, Card, card_has_role
from card_reader_core.models.encounter import Encounter
from card_reader_core.repositories import encounters

MINIMUM_ENCOUNTER_CARDS = 20


def boss_cards(encounter: Encounter) -> list[Card]:
    if encounter.boss_card is None:
        return []
    if encounter.boss_group is None:
        return [encounter.boss_card]
    return [member.card for member in encounter.boss_group.members.all()]


def validation_issues(encounter: Encounter, *, export: bool = False) -> list[str]:
    issues: list[str] = []
    if not export and not encounter.name.strip():
        issues.append("Name is required.")
    boss = encounter.boss_card
    if boss is None or not card_has_role(boss, "boss"):
        issues.append("Select a boss.")
    if encounter.boss_group and encounter.boss_group.anchor_card_id != encounter.boss_card_id:
        issues.append("The boss group primary card changed. Select the boss again.")
    if hasattr(encounter, "total_cards"):
        total = getattr(encounter, "total_cards")
        missing_boss_member = encounter.boss_group is not None and not getattr(
            encounter, "boss_in_group"
        )
        bad_contents = (
            getattr(encounter, "bad_entries")
            or getattr(encounter, "bad_members")
            or getattr(encounter, "bad_sideboards")
        )
    else:
        cards = boss_cards(encounter)
        entries = list(encounter.entries.all())
        total = sum(entry.quantity for entry in entries)
        missing_boss_member = boss is not None and not any(card.id == boss.id for card in cards)
        cards.extend(entry.card for entry in entries)
        for board in encounter.sideboards.all():
            cards.extend(entry.card for entry in board.entries.all())
        bad_contents = any(
            card.card_pool != "evil" or card.lifecycle_status != "active" for card in cards
        )
    if missing_boss_member:
        issues.append("The boss is no longer in its selected group.")
    if not export and total < MINIMUM_ENCOUNTER_CARDS:
        issues.append(f"Add at least {MINIMUM_ENCOUNTER_CARDS} deck cards, excluding boss cards.")
    if bad_contents or (boss and (boss.card_pool != "evil" or boss.lifecycle_status != "active")):
        issues.append("Replace deprecated or non-Evil cards before publishing or exporting.")
    return issues


class EncounterService:
    def normalize(
        self, data: dict[str, Any], existing: Encounter | None = None
    ) -> tuple[dict[str, Any], list[dict[str, Any]] | None, list[dict[str, Any]] | None]:
        fields = {
            key: value
            for key, value in data.items()
            if key
            in {
                "name",
                "description_markup",
                "long_description_markup",
                "visibility",
                "boss_card_id",
                "boss_group_id",
                "factions",
            }
        }
        if "name" in fields:
            fields["name"] = " ".join(fields["name"].split())
        for field in ("description", "long_description"):
            markup_key = f"{field}_markup"
            if markup_key in fields:
                fields[markup_key] = (fields[markup_key] or "").replace("\r\n", "\n")
                fields[field] = render_markup_plain(
                    fields[markup_key], compact=field == "description"
                )
        if "factions" in fields:
            if any(value not in CARD_FACTIONS for value in fields["factions"]):
                raise ValueError("Unknown faction.")
            fields["factions"] = [value for value in CARD_FACTIONS if value in fields["factions"]]
        entries = data.get("entries")
        sideboards = data.get("sideboards")
        old_boards = {board.id: board for board in existing.sideboards.all()} if existing else {}

        def validate_entries(values: list[dict[str, Any]], old_quantities: dict[str, int]) -> None:
            cards = encounters.get_cards([entry["card_id"] for entry in values])
            seen: set[str] = set()
            for entry in values:
                card = cards.get(entry["card_id"])
                if card is None or card.id in seen:
                    raise ValueError("Entries must reference distinct existing cards.")
                seen.add(card.id)
                if type(entry["quantity"]) is not int or entry["quantity"] < 1:
                    raise ValueError("Card quantities must be positive integers.")
                if card.card_pool != "evil" and entry["quantity"] > old_quantities.get(card.id, 0):
                    raise ValueError("Only Evil cards can be added to an Encounter.")

        if entries is not None:
            validate_entries(
                entries,
                {entry.card_id: entry.quantity for entry in existing.entries.all()}
                if existing
                else {},
            )
        seen_boards: set[str] = set()
        if sideboards is not None:
            for board in sideboards:
                board["name"] = " ".join(board["name"].split())
                if not board["name"]:
                    raise ValueError("Sideboard name is required.")
                board_id = board.get("id")
                if board_id and (board_id not in old_boards or board_id in seen_boards):
                    raise ValueError(
                        "Sideboards must reference distinct boards belonging to this Encounter."
                    )
                if board_id:
                    seen_boards.add(board_id)
                old = old_boards.get(board_id)
                validate_entries(
                    board["entries"],
                    {entry.card_id: entry.quantity for entry in old.entries.all()} if old else {},
                )
        boss_id = fields.get("boss_card_id", existing.boss_card_id if existing else None)
        group_id = fields.get("boss_group_id", existing.boss_group_id if existing else None)
        selection_changed = (
            existing is None
            or boss_id != existing.boss_card_id
            or group_id != existing.boss_group_id
        )
        if selection_changed:
            boss = encounters.get_cards([boss_id]).get(boss_id) if boss_id else None
            if boss_id and (
                boss is None
                or boss.card_pool != "evil"
                or not card_has_role(boss, "boss")
                or boss.lifecycle_status != "active"
            ):
                raise ValueError("Select an active Evil boss.")
            if group_id:
                group = encounters.get_group(group_id)
                if group is None or group.anchor_card.id != boss_id:
                    raise ValueError("Select the group's primary boss card.")
                if any(
                    member.card.card_pool != "evil" or member.card.lifecycle_status != "active"
                    for member in group.members.all()
                ):
                    raise ValueError("The boss group must contain active Evil cards only.")
        return fields, entries, sideboards

    def create(self, creator_id: str, key: UUID, data: dict[str, Any]) -> tuple[Encounter, bool]:
        existing, used = encounters.creation_result(creator_id, key)
        if existing:
            return existing, False
        if used:
            raise encounters.EncounterDeleted("The Encounter created by this key has been deleted.")
        fields, entries, sideboards = self.normalize(data)
        record, created = encounters.create_encounter(
            creator_id, key, fields, entries or [], sideboards or []
        )
        result = encounters.get_encounter(str(record.id))
        assert result is not None
        return result, created

    def update(self, encounter: Encounter, data: dict[str, Any], revision: int) -> Encounter:
        fields, entries, sideboards = self.normalize(data, encounter)
        encounters.update_encounter(str(encounter.id), revision, fields, entries, sideboards)
        result = encounters.get_encounter(str(encounter.id))
        assert result is not None
        return result
