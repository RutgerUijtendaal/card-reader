from __future__ import annotations

from typing import cast

from rest_framework import serializers

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import card_payload
from card_reader_core.models import (
    DEFAULT_CARD_LIFECYCLE_FILTER,
    CardGroup,
    CardGroupMember,
    CardLifecycleFilter,
    CardVersion,
    CardVersionImage,
    card_is_visible_for_lifecycle,
)
from card_reader_core.repositories.cards import get_card_image, resolve_image_file_path
from card_reader_core.services.cards import get_card_version_metadata


def card_group_visible_members(group: CardGroup, lifecycle_status: CardLifecycleFilter) -> list[CardGroupMember]:
    members = sorted(group.members.all(), key=lambda member: (member.position, member.id))
    return [member for member in members if card_is_visible_for_lifecycle(member.card, lifecycle_status)]


def _get_card_version_image(version: CardVersion) -> CardVersionImage | None:
    prefetched = cast(list[CardVersionImage] | None, getattr(version, "_prefetched_objects_cache", {}).get("images"))
    if prefetched is None:
        return get_card_image(version.id)

    first_image = None
    for image in prefetched:
        if first_image is None:
            first_image = image
        if resolve_image_file_path(image) is not None:
            return image
    return first_image


def card_group_gallery_payload(
    group: CardGroup,
    *,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
) -> dict[str, object]:
    members = card_group_visible_members(group, lifecycle_status)
    anchor_card_id = group.anchor_card.id
    preview_cards = []
    for member in members:
        version = member.card.latest_version
        if version is None:
            continue
        image = _get_card_version_image(version)
        preview_cards.append(
            {
                "card_id": member.card.id,
                "position": member.position,
                "name": version.name,
                "image_url": card_image_asset_url(image, fallback_url=f"/cards/{member.card.id}/image"),
            }
        )
    anchor_version = group.anchor_card.latest_version
    return {
        "id": group.id,
        "result_type": "card_group",
        "group_id": group.id,
        "group_key": group.key,
        "group_name": group.name,
        "anchor_card_id": anchor_card_id,
        "anchor_card_name": anchor_version.name if anchor_version is not None else group.anchor_card.label,
        "member_count": len(members),
        "preview_cards": preview_cards,
    }


def card_group_detail_payload(
    group: CardGroup,
    *,
    lifecycle_status: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
) -> dict[str, object]:
    anchor_card_id = group.anchor_card.id
    members_payload = []
    for member in card_group_visible_members(group, lifecycle_status):
        version = member.card.latest_version
        if version is None:
            continue
        image = _get_card_version_image(version)
        members_payload.append(
            {
                "position": member.position,
                "is_anchor": member.card.id == anchor_card_id,
                "card": card_payload(
                    member.card,
                    version,
                    image_url=card_image_asset_url(image, fallback_url=f"/cards/{member.card.id}/image"),
                    metadata=get_card_version_metadata(version.id),
                    card_groups=[],
                ),
            }
        )
    return {
        "id": group.id,
        "key": group.key,
        "name": group.name,
        "anchor_card_id": anchor_card_id,
        "member_count": len(members_payload),
        "members": members_payload,
    }


def card_group_admin_payload(group: CardGroup) -> dict[str, object]:
    anchor_version = group.anchor_card.latest_version
    anchor_card_id = group.anchor_card.id
    members = list(group.members.all())
    return {
        "id": group.id,
        "key": group.key,
        "name": group.name,
        "anchor_card_id": anchor_card_id,
        "anchor_card_name": anchor_version.name if anchor_version is not None else group.anchor_card.label,
        "member_count": len(members),
        "members": [card_group_member_admin_payload(member, anchor_card_id) for member in members],
    }


def card_group_member_admin_payload(member: CardGroupMember, anchor_card_id: str) -> dict[str, object]:
    version = member.card.latest_version
    image = None if version is None else _get_card_version_image(version)
    card_id = member.card.id
    return {
        "card_id": card_id,
        "card_label": member.card.label,
        "card_name": version.name if version is not None else member.card.label,
        "position": member.position,
        "is_anchor": card_id == anchor_card_id,
        "image_url": card_image_asset_url(image, fallback_url=f"/cards/{card_id}/image") if version is not None else None,
    }


class CardGroupMemberWriteSerializer(serializers.Serializer[dict[str, object]]):
    card_id = serializers.CharField()
    position = serializers.IntegerField(min_value=1)


class CardGroupWriteSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    anchor_card_id = serializers.CharField(required=False)
    members = CardGroupMemberWriteSerializer(many=True, required=False)
