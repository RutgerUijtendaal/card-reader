from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast

from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer




class PaginatedResult(Protocol):
    @property
    def count(self) -> int: ...

    @property
    def page(self) -> int: ...

    @property
    def page_size(self) -> int: ...


def bad_request(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def not_found(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_404_NOT_FOUND)


def forbidden(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_403_FORBIDDEN)


def serializer_error(serializer: BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)


def paginated_payload(
    page: PaginatedResult,
    results: Sequence[object],
) -> dict[str, object]:
    return {
        "count": page.count,
        "next_page": page.page + 1 if page.page * page.page_size < page.count else None,
        "previous_page": page.page - 1 if page.page > 1 else None,
        "page": page.page,
        "page_size": page.page_size,
        "results": list(results),
    }
