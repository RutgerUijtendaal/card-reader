from __future__ import annotations

from typing import Literal, TypedDict, cast

from rest_framework import serializers


class GalleryTtsCardExportSource(TypedDict):
    type: Literal["gallery"]
    filters: dict[str, object]


class ContentVersionTtsCardExportSource(TypedDict):
    type: Literal["content_version"]
    content_version_id: str


TtsCardExportSource = GalleryTtsCardExportSource | ContentVersionTtsCardExportSource


class TtsCardExportSourceSerializer(serializers.Serializer[dict[str, object]]):
    type = serializers.ChoiceField(choices=("gallery", "content_version"))
    filters = serializers.DictField(required=False, default=dict)
    content_version_id = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        source_type = attrs.get("type")
        if source_type == "gallery":
            if attrs.get("content_version_id") is not None:
                raise serializers.ValidationError({"content_version_id": "Not valid for a gallery export."})
            return attrs
        if not attrs.get("content_version_id"):
            raise serializers.ValidationError({"content_version_id": "This field is required."})
        if attrs.get("filters"):
            raise serializers.ValidationError({"filters": "Not valid for a content-version export."})
        return attrs


class TtsCardExportRequestSerializer(serializers.Serializer[dict[str, object]]):
    source = TtsCardExportSourceSerializer()  # type: ignore[assignment]

    def validated_source(self) -> TtsCardExportSource:
        return cast(TtsCardExportSource, self.validated_data["source"])
