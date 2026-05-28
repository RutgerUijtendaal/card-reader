from __future__ import annotations

from rest_framework import serializers

from card_reader_core.services.card_merges import CardMergePreview


class CardMergeRequestSerializer(serializers.Serializer[dict[str, object]]):
    target_card_id = serializers.CharField(required=True, allow_blank=False)
    source_card_ids = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=True,
        allow_empty=False,
    )


def card_merge_preview_payload(preview: CardMergePreview) -> dict[str, object]:
    return {
        "target": preview.target.__dict__,
        "sources": [source.__dict__ for source in preview.sources],
        "aliases": [alias.__dict__ for alias in preview.aliases],
        "relations": preview.relations.__dict__,
        "resulting_version_count": preview.resulting_version_count,
        "blocking_conflicts": preview.blocking_conflicts,
        "can_apply": len(preview.blocking_conflicts) == 0,
    }
