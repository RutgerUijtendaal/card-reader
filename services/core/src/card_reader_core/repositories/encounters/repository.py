from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Exists, F, OuterRef, Prefetch, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce, Trim

from card_reader_core.models import Card, CardGroup, CardGroupMember, CardRoleAssignment, now_utc
from card_reader_core.models.encounter import Encounter, EncounterCreation, EncounterEntry


class EncounterConflict(ValueError):
    pass


class EncounterDeleted(ValueError):
    pass


def card_queryset() -> QuerySet[Card]:
    return Card.objects.select_related(
        "latest_version", "latest_version__template", "latest_version__previous_version"
    ).prefetch_related(
        "role_assignments",
        "faction_assignments",
        "mana_family_assignments",
        "latest_version__images",
        "latest_version__card_version_symbols__symbol",
        "latest_version__card_version_keywords__keyword",
        "latest_version__card_version_tags__tag",
        "latest_version__card_version_types__type",
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
    *, staff: bool, minimum_cards: int, query: str, factions: list[str], page: int, page_size: int
) -> tuple[int, list[Encounter]]:
    records = (
        encounter_queryset(detail=False) if staff else public_queryset(minimum_cards, detail=False)
    )
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


@transaction.atomic
def create_encounter(
    creator_id: str, key: UUID, fields: dict[str, Any], entries: list[dict[str, Any]]
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
    receipt.encounter = encounter
    receipt.save(update_fields=["encounter"])
    return encounter, True


@transaction.atomic
def update_encounter(
    encounter_id: str, revision: int, fields: dict[str, Any], entries: list[dict[str, Any]] | None
) -> None:
    changed = Encounter.objects.filter(pk=encounter_id, revision=revision).update(
        **fields, revision=F("revision") + 1, updated_at=now_utc()
    )
    if not changed:
        raise EncounterConflict(
            "Another staff member changed this Encounter. Reload it before saving."
        )
    if entries is not None:
        replace_entries(Encounter.objects.get(pk=encounter_id), entries)


def delete_encounter(encounter_id: str, revision: int) -> bool:
    with transaction.atomic():
        # The conditional write also serializes deletion with concurrent edits on SQLite.
        if not Encounter.objects.filter(pk=encounter_id, revision=revision).update(
            revision=F("revision") + 1
        ):
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
