from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from rest_framework import serializers
from rest_framework.response import Response

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import card_payload
from card_reader_core.models import CardGroup, CardGroupMember
from card_reader_core.repositories.cards_repository import get_card_image
from card_reader_core.services.cards import get_card_version_metadata


def card_group_gallery_payload(group: CardGroup) -> dict[str, object]:
    members = list(cast(Any, group).members.all())
    anchor_card_id = group.anchor_card.id
    preview_cards = []
    for member in members[:3]:
        version = member.card.latest_version
        if version is None:
            continue
        image = get_card_image(version.id)
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


def card_group_detail_payload(group: CardGroup) -> dict[str, object]:
    anchor_card_id = group.anchor_card.id
    members_payload = []
    for member in cast(Any, group).members.all():
        version = member.card.latest_version
        if version is None:
            continue
        image = get_card_image(version.id)
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
    members = list(cast(Any, group).members.all())
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
    image = None if version is None else get_card_image(version.id)
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


def serializer_error(serializer: serializers.BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=400)
