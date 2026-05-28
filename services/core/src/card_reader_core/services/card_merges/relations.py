from __future__ import annotations

from card_reader_core.models import CardGroup, CardGroupMember, Deck, DeckEntry, DeckSideboardEntry, now_utc

from .types import CardMergeRelationPreview


def preview_relation_changes(*, target_id: str, source_ids: list[str]) -> CardMergeRelationPreview:
    return CardMergeRelationPreview(
        deck_entry_collisions=count_deck_entry_collisions(target_id, source_ids),
        sideboard_entry_collisions=count_sideboard_entry_collisions(target_id, source_ids),
        group_member_collisions=count_group_member_collisions(target_id, source_ids),
        hero_references=Deck.objects.filter(hero_card_id__in=source_ids).count(),
        anchored_groups=CardGroup.objects.filter(anchor_card_id__in=source_ids).count(),
    )


def count_deck_entry_collisions(target_id: str, source_ids: list[str]) -> int:
    collision_count = 0
    for deck_id in DeckEntry.objects.filter(card_id__in=source_ids).values_list("deck_id", flat=True):
        if DeckEntry.objects.filter(deck_id=deck_id, card_id=target_id).exists():
            collision_count += 1
    return collision_count


def count_sideboard_entry_collisions(target_id: str, source_ids: list[str]) -> int:
    collision_count = 0
    for sideboard_id in DeckSideboardEntry.objects.filter(card_id__in=source_ids).values_list("sideboard_id", flat=True):
        if DeckSideboardEntry.objects.filter(sideboard_id=sideboard_id, card_id=target_id).exists():
            collision_count += 1
    return collision_count


def count_group_member_collisions(target_id: str, source_ids: list[str]) -> int:
    collision_count = 0
    for group_id in CardGroupMember.objects.filter(card_id__in=source_ids).values_list("group_id", flat=True):
        if CardGroupMember.objects.filter(group_id=group_id, card_id=target_id).exists():
            collision_count += 1
    return collision_count


def merge_deck_references(target_id: str, source_ids: list[str]) -> None:
    Deck.objects.filter(hero_card_id__in=source_ids).update(hero_card_id=target_id, updated_at=now_utc())

    for entry in list(DeckEntry.objects.filter(card_id__in=source_ids).select_for_update()):
        deck_id = str(getattr(entry, "deck_id"))
        existing = DeckEntry.objects.filter(deck_id=deck_id, card_id=target_id).first()
        if existing is None:
            setattr(entry, "card_id", target_id)
            entry.updated_at = now_utc()
            entry.save(update_fields=["card", "updated_at"])
            continue
        existing.quantity += entry.quantity
        existing.updated_at = now_utc()
        existing.save(update_fields=["quantity", "updated_at"])
        entry.delete()

    for sideboard_entry in list(DeckSideboardEntry.objects.filter(card_id__in=source_ids).select_for_update()):
        sideboard_id = str(getattr(sideboard_entry, "sideboard_id"))
        existing_sideboard_entry = DeckSideboardEntry.objects.filter(sideboard_id=sideboard_id, card_id=target_id).first()
        if existing_sideboard_entry is None:
            setattr(sideboard_entry, "card_id", target_id)
            sideboard_entry.updated_at = now_utc()
            sideboard_entry.save(update_fields=["card", "updated_at"])
            continue
        existing_sideboard_entry.quantity += sideboard_entry.quantity
        existing_sideboard_entry.updated_at = now_utc()
        existing_sideboard_entry.save(update_fields=["quantity", "updated_at"])
        sideboard_entry.delete()


def merge_card_group_references(target_id: str, source_ids: list[str]) -> None:
    CardGroup.objects.filter(anchor_card_id__in=source_ids).update(anchor_card_id=target_id, updated_at=now_utc())
    affected_group_ids: set[str] = set()
    for member in list(CardGroupMember.objects.filter(card_id__in=source_ids).select_for_update()):
        group_id = str(getattr(member, "group_id"))
        affected_group_ids.add(group_id)
        existing = CardGroupMember.objects.filter(group_id=group_id, card_id=target_id).first()
        if existing is None:
            setattr(member, "card_id", target_id)
            member.updated_at = now_utc()
            member.save(update_fields=["card", "updated_at"])
            continue
        member.delete()

    for group_id in affected_group_ids:
        members = list(CardGroupMember.objects.filter(group_id=group_id).order_by("position", "created_at", "id"))
        for index, member in enumerate(members, start=1):
            if member.position != index:
                member.position = index
                member.updated_at = now_utc()
                member.save(update_fields=["position", "updated_at"])
