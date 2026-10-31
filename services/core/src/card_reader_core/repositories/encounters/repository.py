from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce, Trim

from card_reader_core.models import (
    Card,
    CardGroup,
    CardGroupMember,
    CardRoleAssignment,
    CardVersionImage,
    now_utc,
)
from card_reader_core.models.encounter import (
    Encounter,
    EncounterCreation,
    EncounterEntry,
    EncounterSideboard,
    EncounterSideboardEntry,
)
from card_reader_core.repositories.cards import card_version_metadata_prefetches


class EncounterConflict(ValueError):
    pass


class EncounterForbidden(PermissionError):
    pass


class EncounterDeleted(ValueError):
    pass


def card_queryset() -> QuerySet[Card]:
    return (
        Card.objects.select_related(
            "latest_version", "latest_version__template", "latest_version__content_version"
        )
        .defer(
            "latest_version__parsed_snapshot_json",
            "latest_version__field_sources_json",
            "latest_version__template__definition_json",
        )
        .prefetch_related(
            "role_assignments",
            "faction_assignments",
            "mana_family_assignments",
            Prefetch(
                "latest_version__images", queryset=CardVersionImage.objects.order_by("-created_at")
            ),
            *card_version_metadata_prefetches("latest_version"),
        )
    )


def encounter_queryset(*, detail: bool = True) -> QuerySet[Encounter]:
    total = (
        EncounterEntry.objects.filter(encounter_id=OuterRef("pk"))
        .order_by()
        .values("encounter_id")
        .annotate(value=Sum("quantity"))
        .values("value")
    )
    bad_entries = EncounterEntry.objects.filter(encounter_id=OuterRef("pk")).exclude(
        card__card_pool="evil", card__lifecycle_status="active"
    )
    bad_sideboards = EncounterSideboardEntry.objects.filter(
        sideboard__encounter_id=OuterRef("pk")
    ).exclude(card__card_pool="evil", card__lifecycle_status="active")
    board_count = (
        EncounterSideboard.objects.filter(encounter_id=OuterRef("pk"))
        .order_by()
        .values("encounter_id")
        .annotate(value=Count("pk"))
        .values("value")
    )
    bad_members = CardGroupMember.objects.filter(group_id=OuterRef("boss_group_id")).exclude(
        card__card_pool="evil", card__lifecycle_status="active"
    )
    boss_role = CardRoleAssignment.objects.filter(card_id=OuterRef("boss_card_id"), role="boss")
    boss_member = CardGroupMember.objects.filter(
        group_id=OuterRef("boss_group_id"), card_id=OuterRef("boss_card_id")
    )
    records = (
        Encounter.objects.annotate(
            total_cards=Coalesce(Subquery(total), 0),
            bad_entries=Exists(bad_entries),
            bad_sideboards=Exists(bad_sideboards),
            sideboard_count=Coalesce(Subquery(board_count), 0),
            bad_members=Exists(bad_members),
            has_boss_role=Exists(boss_role),
            boss_in_group=Exists(boss_member),
            trimmed_name=Trim("name"),
        )
        .select_related("creator", "boss_group")
        .prefetch_related(
            Prefetch("boss_card", queryset=card_queryset()),
        )
    )
    if not detail:
        return records
    return records.prefetch_related(
        Prefetch(
            "sideboards",
            queryset=EncounterSideboard.objects.prefetch_related(
                Prefetch(
                    "entries",
                    queryset=EncounterSideboardEntry.objects.prefetch_related(
                        Prefetch("card", queryset=card_queryset())
                    ),
                )
            ),
        ),
        Prefetch(
            "entries",
            queryset=EncounterEntry.objects.prefetch_related(
                Prefetch("card", queryset=card_queryset())
            ),
        ),
        Prefetch(
            "boss_group__members",
            queryset=CardGroupMember.objects.order_by("position").prefetch_related(
                Prefetch("card", queryset=card_queryset())
            ),
        ),
    )


def public_queryset(minimum_cards: int, *, detail: bool = True) -> QuerySet[Encounter]:
    return (
        encounter_queryset(detail=detail)
        .filter(
            visibility="public",
            total_cards__gte=minimum_cards,
            bad_entries=False,
            bad_sideboards=False,
            bad_members=False,
            has_boss_role=True,
            boss_card__card_pool="evil",
            boss_card__lifecycle_status="active",
        )
        .exclude(trimmed_name="")
        .filter(
            Q(boss_group__isnull=True)
            | Q(boss_group__anchor_card_id=F("boss_card_id"), boss_in_group=True)
        )
    )


def get_encounter(encounter_id: str) -> Encounter | None:
    return encounter_queryset().filter(pk=encounter_id).first()


def list_encounters(
    *,
    staff: bool,
    minimum_cards: int,
    query: str,
    factions: list[str],
    page: int,
    page_size: int,
    owner_id: str | None = None,
    is_official: bool | None = None,
) -> tuple[int, list[Encounter]]:
    records = (
        encounter_queryset(detail=False)
        if staff or owner_id
        else public_queryset(minimum_cards, detail=False)
    )
    if owner_id is not None:
        records = records.filter(creator_id=owner_id)
    if is_official is not None:
        records = records.filter(is_official=is_official)
    records = records.filter(name__icontains=query)
    if factions:
        match = Q()
        for faction in factions:
            # SQLite supports scalar JSON lookups, but not array containment.
            for index in range(5):
                match |= Q(**{f"factions__{index}": faction})
        records = records.filter(match)
    return records.count(), list(records[(page - 1) * page_size : page * page_size])


def get_cards(ids: list[str]) -> dict[str, Card]:
    return {card.id: card for card in card_queryset().filter(pk__in=ids)}


def get_group(group_id: str) -> CardGroup | None:
    return CardGroup.objects.prefetch_related("members__card").filter(pk=group_id).first()


def creation_result(creator_id: str, key: UUID) -> tuple[Encounter | None, bool]:
    receipt = EncounterCreation.objects.filter(
        creator_id=creator_id, client_creation_id=key
    ).first()
    return (
        get_encounter(str(receipt.encounter_id)) if receipt and receipt.encounter_id else None,
        receipt is not None,
    )


def replace_entries(encounter: Encounter, entries: list[dict[str, Any]]) -> None:
    encounter.entries.all().delete()
    EncounterEntry.objects.bulk_create(
        [
            EncounterEntry(
                encounter=encounter,
                card_id=entry["card_id"],
                quantity=entry["quantity"],
                position=position,
            )
            for position, entry in enumerate(entries)
        ]
    )


def replace_sideboards(encounter: Encounter, sideboards: list[dict[str, Any]]) -> None:
    retained = []
    for position, data in enumerate(sideboards):
        board_id = data.get("id")
        if board_id:
            board = encounter.sideboards.get(pk=board_id)
            board.name, board.position = data["name"], position
            board.save(update_fields=["name", "position", "updated_at"])
        else:
            board = EncounterSideboard.objects.create(
                encounter=encounter, name=data["name"], position=position
            )
        retained.append(board.id)
        board.entries.all().delete()
        EncounterSideboardEntry.objects.bulk_create(
            [
                EncounterSideboardEntry(
                    sideboard=board,
                    card_id=entry["card_id"],
                    quantity=entry["quantity"],
                    position=index,
                )
                for index, entry in enumerate(data["entries"])
            ]
        )
    encounter.sideboards.exclude(pk__in=retained).delete()


@transaction.atomic
def create_encounter(
    creator_id: str,
    key: UUID,
    fields: dict[str, Any],
    entries: list[dict[str, Any]],
    sideboards: list[dict[str, Any]],
) -> tuple[Encounter, bool]:
    receipt, created = EncounterCreation.objects.get_or_create(
        creator_id=creator_id, client_creation_id=key
    )
    if not created:
        existing = get_encounter(str(receipt.encounter_id)) if receipt.encounter_id else None
        if existing is None:
            raise EncounterDeleted("The Encounter created by this key has been deleted.")
        return existing, False
    encounter = Encounter.objects.create(creator_id=creator_id, **fields)
    replace_entries(encounter, entries)
    replace_sideboards(encounter, sideboards)
    receipt.encounter = encounter
    receipt.save(update_fields=["encounter"])
    return encounter, True


@transaction.atomic
def update_encounter(
    encounter_id: str,
    revision: int,
    fields: dict[str, Any],
    entries: list[dict[str, Any]] | None,
    sideboards: list[dict[str, Any]] | None,
    *,
    actor_id: str | None,
    is_staff: bool,
) -> None:
    if "is_official" in fields and not is_staff:
        raise EncounterForbidden("Only staff may change Official status.")
    allowed = mutable_encounters(actor_id=actor_id, is_staff=is_staff)
    changed = allowed.filter(pk=encounter_id, revision=revision).update(
        **fields, revision=F("revision") + 1, updated_at=now_utc()
    )
    if not changed:
        if not allowed.filter(pk=encounter_id).exists():
            raise EncounterForbidden("You no longer have permission to edit this Encounter.")
        raise EncounterConflict("Another person changed this Encounter. Reload it before saving.")
    if entries is not None:
        replace_entries(Encounter.objects.get(pk=encounter_id), entries)
    if sideboards is not None:
        replace_sideboards(Encounter.objects.get(pk=encounter_id), sideboards)


def mutable_encounters(*, actor_id: str | None, is_staff: bool) -> QuerySet[Encounter]:
    # Apply the permission predicate to the conditional revision write, not just a prior read.
    records = Encounter.objects.all()
    return records if is_staff else records.filter(creator_id=actor_id, is_official=False)


def delete_encounter(
    encounter_id: str, revision: int, *, actor_id: str | None, is_staff: bool
) -> bool:
    with transaction.atomic():
        # The conditional write also serializes deletion with concurrent edits on SQLite.
        allowed = mutable_encounters(actor_id=actor_id, is_staff=is_staff)
        if not allowed.filter(pk=encounter_id, revision=revision).update(
            revision=F("revision") + 1
        ):
            if not allowed.filter(pk=encounter_id).exists():
                raise EncounterForbidden("You no longer have permission to delete this Encounter.")
            raise EncounterConflict("The Encounter changed. Reload it before deleting.")
        count, _ = Encounter.objects.filter(pk=encounter_id).delete()
        return count > 0


def retarget_encounter_cards(target_id: str, source_ids: list[str]) -> None:
    affected = set(
        EncounterEntry.objects.filter(card_id__in=source_ids).values_list("encounter_id", flat=True)
    )
    affected.update(
        Encounter.objects.filter(boss_card_id__in=source_ids).values_list("id", flat=True)
    )
    affected.update(
        EncounterSideboardEntry.objects.filter(card_id__in=source_ids).values_list(
            "sideboard__encounter_id", flat=True
        )
    )
    for sideboard_entry in EncounterSideboardEntry.objects.filter(card_id__in=source_ids).order_by(
        "position", "id"
    ):
        existing_sideboard_entry = EncounterSideboardEntry.objects.filter(
            sideboard=sideboard_entry.sideboard, card_id=target_id
        ).first()
        if existing_sideboard_entry is None:
            sideboard_entry.card_id = target_id
            sideboard_entry.save(update_fields=["card"])
        else:
            existing_sideboard_entry.quantity += sideboard_entry.quantity
            existing_sideboard_entry.position = min(
                existing_sideboard_entry.position, sideboard_entry.position
            )
            existing_sideboard_entry.save(update_fields=["quantity", "position"])
            sideboard_entry.delete()
    Encounter.objects.filter(boss_card_id__in=source_ids).update(boss_card_id=target_id)
    for entry in EncounterEntry.objects.filter(card_id__in=source_ids).order_by("position", "id"):
        existing = EncounterEntry.objects.filter(
            encounter=entry.encounter, card_id=target_id
        ).first()
        if existing is None:
            entry.card_id = target_id
            entry.save(update_fields=["card"])
        else:
            existing.quantity += entry.quantity
            existing.position = min(existing.position, entry.position)
            existing.save(update_fields=["quantity", "position"])
            entry.delete()
    Encounter.objects.filter(pk__in=affected).update(
        revision=F("revision") + 1, updated_at=now_utc()
    )
