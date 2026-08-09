from __future__ import annotations

from rest_framework import serializers


class OperationsOverviewQuerySerializer(serializers.Serializer[dict[str, object]]):
    include_items = serializers.BooleanField(required=False, default=True)


class OperationsQueueQuerySerializer(serializers.Serializer[dict[str, object]]):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        default=20,
    )
