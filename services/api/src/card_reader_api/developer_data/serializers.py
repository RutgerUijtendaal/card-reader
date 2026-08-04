from __future__ import annotations

from rest_framework import serializers


class DeveloperDataCodeExchangeSerializer(serializers.Serializer[dict[str, str]]):
    code = serializers.CharField(max_length=40, trim_whitespace=True)
    bundle_version = serializers.CharField(max_length=80, trim_whitespace=True)
