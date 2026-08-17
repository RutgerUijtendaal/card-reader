from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ValidatedStringValuesMixin:
    """Typed accessors shared by serializers that expose string query values."""

    validated_data: Mapping[str, Any]

    def _string_or_none(self, key: str) -> str | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, str) else None

    def _string_list_or_none(self, key: str) -> list[str] | None:
        value = self.validated_data.get(key)
        if not isinstance(value, list):
            return None
        strings = [item for item in value if isinstance(item, str)]
        return strings or None
