from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from card_reader_api.catalog.serializers import (
    CatalogEntryWriteSerializer,
    SuggestionAcceptSerializer,
    SuggestionStatusQuerySerializer,
    SymbolAssetUploadSerializer,
    SymbolWriteSerializer,
    keyword_detail_payload,
    keyword_payload,
    suggestion_payload,
    symbol_detail_payload,
    symbol_payload,
    tag_detail_payload,
    tag_payload,
    type_detail_payload,
    type_payload,
)
from card_reader_core.services.catalog import CatalogService
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path

_ALLOWED_SYMBOL_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


class CatalogView(APIView):
    def get(self, _request: Request) -> Response:
        data = CatalogService().list_catalog()
        return Response(
            {
                "known": {
                    "keywords": [keyword_payload(item) for item in data["known"]["keywords"]],
                    "tags": [tag_payload(item) for item in data["known"]["tags"]],
                    "symbols": [symbol_payload(item) for item in data["known"]["symbols"]],
                    "types": [type_payload(item) for item in data["known"]["types"]],
                },
                "suggested": {
                    "tags": [suggestion_payload(item) for item in data["suggested"]["tags"]],
                    "types": [suggestion_payload(item) for item in data["suggested"]["types"]],
                },
            }
        )


class KeywordCreateView(APIView):
    def post(self, request: Request) -> Response:
        return _create_simple(request, "keyword", keyword_payload, include_identifiers=True)


class KeywordDetailView(APIView):
    def get(self, _request: Request, entry_id: str) -> Response:
        detail = CatalogService().get_keyword_detail(entry_id=entry_id)
        if detail is None:
            return _not_found("Keyword not found")
        return Response(keyword_detail_payload(detail))

    def patch(self, request: Request, entry_id: str) -> Response:
        return _update_simple(request, entry_id, "keyword", keyword_payload, include_identifiers=True)

    def delete(self, _request: Request, entry_id: str) -> Response:
        return _delete_simple(entry_id, "keyword", "Keyword")


class TagCreateView(APIView):
    def post(self, request: Request) -> Response:
        return _create_simple(request, "tag", tag_payload, include_identifiers=True)


class TagDetailView(APIView):
    def get(self, _request: Request, entry_id: str) -> Response:
        detail = CatalogService().get_tag_detail(entry_id=entry_id)
        if detail is None:
            return _not_found("Tag not found")
        return Response(tag_detail_payload(detail))

    def patch(self, request: Request, entry_id: str) -> Response:
        return _update_simple(request, entry_id, "tag", tag_payload, include_identifiers=True)

    def delete(self, _request: Request, entry_id: str) -> Response:
        return _delete_simple(entry_id, "tag", "Tag")


class TypeCreateView(APIView):
    def post(self, request: Request) -> Response:
        return _create_simple(request, "type", type_payload, include_identifiers=True)


class TypeDetailView(APIView):
    def get(self, _request: Request, entry_id: str) -> Response:
        detail = CatalogService().get_type_detail(entry_id=entry_id)
        if detail is None:
            return _not_found("Type not found")
        return Response(type_detail_payload(detail))

    def patch(self, request: Request, entry_id: str) -> Response:
        return _update_simple(request, entry_id, "type", type_payload, include_identifiers=True)

    def delete(self, _request: Request, entry_id: str) -> Response:
        return _delete_simple(entry_id, "type", "Type")


class SymbolCreateView(APIView):
    def post(self, request: Request) -> Response:
        serializer = SymbolWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        try:
            symbol = CatalogService().create_symbol(
                label=serializer.validated_data["label"],
                key=serializer.validated_data.get("key"),
                symbol_type=serializer.validated_data.get("symbol_type"),
                detector_type=serializer.validated_data.get("detector_type"),
                detection_config_json=serializer.validated_data.get("detection_config_json"),
                text_enrichment_json=serializer.validated_data.get("text_enrichment_json"),
                reference_assets_json=serializer.validated_data.get("reference_assets_json"),
                text_token=serializer.validated_data.get("text_token"),
                enabled=serializer.validated_data.get("enabled"),
            )
        except ValueError as exc:
            return _bad_request(str(exc))
        return Response(symbol_payload(symbol))


class SymbolDetailView(APIView):
    def get(self, _request: Request, entry_id: str) -> Response:
        detail = CatalogService().get_symbol_detail(entry_id=entry_id)
        if detail is None:
            return _not_found("Symbol not found")
        return Response(symbol_detail_payload(detail))

    def patch(self, request: Request, entry_id: str) -> Response:
        serializer = SymbolWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        try:
            symbol = CatalogService().update_symbol(
                entry_id=entry_id,
                label=serializer.validated_data.get("label"),
                key=serializer.validated_data.get("key"),
                symbol_type=serializer.validated_data.get("symbol_type"),
                detector_type=serializer.validated_data.get("detector_type"),
                detection_config_json=serializer.validated_data.get("detection_config_json"),
                text_enrichment_json=serializer.validated_data.get("text_enrichment_json"),
                reference_assets_json=serializer.validated_data.get("reference_assets_json"),
                text_token=serializer.validated_data.get("text_token"),
                enabled=serializer.validated_data.get("enabled"),
            )
        except ValueError as exc:
            return _bad_request(str(exc))
        if symbol is None:
            return _not_found("Symbol not found")
        return Response(symbol_payload(symbol))

    def delete(self, _request: Request, entry_id: str) -> Response:
        return _delete_simple(entry_id, "symbol", "Symbol")


class SymbolAssetUploadView(APIView):
    def post(self, request: Request) -> Response:
        serializer = SymbolAssetUploadSerializer(data={"file": request.FILES.get("file")})
        if not serializer.is_valid():
            return _serializer_error(serializer)
        upload = serializer.validated_data["file"]

        filename = Path(upload.name or "").name
        suffix = Path(filename).suffix.lower()
        if suffix not in _ALLOWED_SYMBOL_ASSET_SUFFIXES:
            return _bad_request("Unsupported symbol asset file type. Use png/jpg/jpeg/webp/bmp/tif/tiff.")

        target_path = _store_symbol_asset(upload, filename, suffix)
        if target_path.stat().st_size == 0:
            target_path.unlink(missing_ok=True)
            return _bad_request("Uploaded file is empty.")

        return Response(
            {
                "relative_path": str(Path("uploads") / target_path.name).replace("\\", "/"),
                "absolute_path": str(target_path),
            }
        )


class SuggestionListView(APIView):
    def get(self, request: Request, kind: str) -> Response:
        serializer = SuggestionStatusQuerySerializer(data={"status": request.query_params.get("status")})
        if not serializer.is_valid():
            return _serializer_error(serializer)
        try:
            normalized_kind = _normalize_suggestion_kind(kind)
        except ValueError as exc:
            return _bad_request(str(exc))
        suggestions = CatalogService().list_suggestions(
            kind=normalized_kind,
            status=serializer.validated_data.get("status"),
        )
        return Response([suggestion_payload(item) for item in suggestions])


class SuggestionDetailView(APIView):
    def get(self, _request: Request, kind: str, entry_id: str) -> Response:
        try:
            normalized_kind = _normalize_suggestion_kind(kind)
        except ValueError as exc:
            return _bad_request(str(exc))
        suggestion = CatalogService().get_suggestion_detail(suggestion_id=entry_id)
        if suggestion is None or suggestion["kind"] != normalized_kind:
            return _not_found("Suggestion not found")
        return Response(suggestion_payload(suggestion))


class SuggestionAcceptView(APIView):
    def post(self, request: Request, kind: str, entry_id: str) -> Response:
        serializer = SuggestionAcceptSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        try:
            normalized_kind = _normalize_suggestion_kind(kind)
        except ValueError as exc:
            return _bad_request(str(exc))
        service = CatalogService()
        try:
            if serializer.validated_data.get("target_id"):
                suggestion = service.accept_suggestion_to_existing(
                    suggestion_id=entry_id,
                    target_id=serializer.validated_data["target_id"],
                )
            else:
                suggestion = service.accept_suggestion_as_new(
                    suggestion_id=entry_id,
                    label=serializer.validated_data.get("label"),
                    key=serializer.validated_data.get("key"),
                )
        except ValueError as exc:
            return _bad_request(str(exc))
        detail = None if suggestion is None else service.get_suggestion_detail(suggestion_id=suggestion.id)
        if detail is None or detail["kind"] != normalized_kind:
            return _not_found("Suggestion not found")
        return Response(suggestion_payload(detail))


class SuggestionRejectView(APIView):
    def post(self, _request: Request, kind: str, entry_id: str) -> Response:
        try:
            normalized_kind = _normalize_suggestion_kind(kind)
        except ValueError as exc:
            return _bad_request(str(exc))
        service = CatalogService()
        suggestion = service.reject_suggestion(suggestion_id=entry_id)
        detail = None if suggestion is None else service.get_suggestion_detail(suggestion_id=suggestion.id)
        if detail is None or detail["kind"] != normalized_kind:
            return _not_found("Suggestion not found")
        return Response(suggestion_payload(detail))


def _create_simple(
    request: Request,
    kind: str,
    payload: Callable[[Any], dict[str, object]],
    *,
    include_identifiers: bool = False,
) -> Response:
    serializer = CatalogEntryWriteSerializer(data=request.data)
    if not serializer.is_valid():
        return _serializer_error(serializer)
    identifiers = serializer.validated_data.get("identifiers") if include_identifiers else None
    try:
        row = getattr(CatalogService(), f"create_{kind}")(
            label=serializer.validated_data["label"],
            key=serializer.validated_data.get("key"),
            identifiers=identifiers,
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return Response(payload(row))


def _update_simple(
    request: Request,
    entry_id: str,
    kind: str,
    payload: Callable[[Any], dict[str, object]],
    *,
    include_identifiers: bool = False,
) -> Response:
    serializer = CatalogEntryWriteSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return _serializer_error(serializer)
    identifiers = serializer.validated_data.get("identifiers") if include_identifiers else None
    try:
        row = getattr(CatalogService(), f"update_{kind}")(
            entry_id=entry_id,
            label=serializer.validated_data.get("label"),
            key=serializer.validated_data.get("key"),
            identifiers=identifiers,
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    if row is None:
        return _not_found(f"{kind.title()} not found")
    return Response(payload(row))


def _delete_simple(entry_id: str, kind: str, label: str) -> Response:
    deleted = getattr(CatalogService(), f"delete_{kind}")(entry_id=entry_id)
    if not deleted:
        return _not_found(f"{label} not found")
    return Response(status=status.HTTP_204_NO_CONTENT)


def _store_symbol_asset(upload: UploadedFile, filename: str, suffix: str) -> Path:
    stem = Path(filename).stem.strip().lower()
    safe_stem = re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-") or "symbol"
    relative_path = build_storage_relative_path("symbols", "uploads", f"{safe_stem}-{uuid4().hex[:8]}{suffix}")
    target_path = resolve_storage_path(relative_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as stream:
        for chunk in upload.chunks():
            stream.write(chunk)
    return target_path


def _normalize_suggestion_kind(kind: str) -> str:
    normalized = kind.strip().lower()
    if normalized not in {"tag", "type"}:
        raise ValueError("Suggestion kind must be tag or type")
    return normalized


def _bad_request(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _not_found(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_404_NOT_FOUND)


def _serializer_error(serializer: BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)
