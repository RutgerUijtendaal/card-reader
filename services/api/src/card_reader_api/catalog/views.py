from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.catalog.serializers import keyword_payload, symbol_payload, tag_payload, type_payload
from card_reader_core.services.catalog import CatalogService
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path

_ALLOWED_SYMBOL_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


class CatalogView(APIView):
    def get(self, _request: Request) -> Response:
        data = CatalogService().list_catalog()
        return Response(
            {
                "keywords": [keyword_payload(item) for item in data["keywords"]],
                "tags": [tag_payload(item) for item in data["tags"]],
                "symbols": [symbol_payload(item) for item in data["symbols"]],
                "types": [type_payload(item) for item in data["types"]],
            }
        )


class KeywordCreateView(APIView):
    def post(self, request: Request) -> Response:
        return _create_simple(request, "keyword", keyword_payload, include_identifiers=True)


class KeywordDetailView(APIView):
    def patch(self, request: Request, entry_id: str) -> Response:
        return _update_simple(request, entry_id, "keyword", keyword_payload, include_identifiers=True)

    def delete(self, _request: Request, entry_id: str) -> Response:
        return _delete_simple(entry_id, "keyword", "Keyword")


class TagCreateView(APIView):
    def post(self, request: Request) -> Response:
        return _create_simple(request, "tag", tag_payload, include_identifiers=True)


class TagDetailView(APIView):
    def patch(self, request: Request, entry_id: str) -> Response:
        return _update_simple(request, entry_id, "tag", tag_payload, include_identifiers=True)

    def delete(self, _request: Request, entry_id: str) -> Response:
        return _delete_simple(entry_id, "tag", "Tag")


class TypeCreateView(APIView):
    def post(self, request: Request) -> Response:
        return _create_simple(request, "type", type_payload, include_identifiers=True)


class TypeDetailView(APIView):
    def patch(self, request: Request, entry_id: str) -> Response:
        return _update_simple(request, entry_id, "type", type_payload, include_identifiers=True)

    def delete(self, _request: Request, entry_id: str) -> Response:
        return _delete_simple(entry_id, "type", "Type")


class SymbolCreateView(APIView):
    def post(self, request: Request) -> Response:
        label = request.data.get("label")
        if label is None:
            return _bad_request("label is required")
        try:
            symbol = CatalogService().create_symbol(
                label=str(label),
                key=request.data.get("key"),
                symbol_type=request.data.get("symbol_type"),
                detector_type=request.data.get("detector_type"),
                detection_config_json=request.data.get("detection_config_json"),
                reference_assets_json=request.data.get("reference_assets_json"),
                text_token=request.data.get("text_token"),
                enabled=request.data.get("enabled"),
            )
        except ValueError as exc:
            return _bad_request(str(exc))
        return Response(symbol_payload(symbol))


class SymbolDetailView(APIView):
    def patch(self, request: Request, entry_id: str) -> Response:
        try:
            symbol = CatalogService().update_symbol(
                entry_id=entry_id,
                label=request.data.get("label"),
                key=request.data.get("key"),
                symbol_type=request.data.get("symbol_type"),
                detector_type=request.data.get("detector_type"),
                detection_config_json=request.data.get("detection_config_json"),
                reference_assets_json=request.data.get("reference_assets_json"),
                text_token=request.data.get("text_token"),
                enabled=request.data.get("enabled"),
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
        upload = request.FILES.get("file")
        if upload is None:
            return _bad_request("file is required")

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


def _create_simple(
    request: Request,
    kind: str,
    payload: Callable[[Any], dict[str, object]],
    *,
    include_identifiers: bool = False,
) -> Response:
    label = request.data.get("label")
    if label is None:
        return _bad_request("label is required")
    identifiers = None
    if include_identifiers:
        identifiers = request.data.get("identifiers")
        if identifiers is not None and not isinstance(identifiers, list):
            return _bad_request("identifiers must be an array of strings")
        if isinstance(identifiers, list) and not all(isinstance(item, str) for item in identifiers):
            return _bad_request("identifiers must be an array of strings")
    try:
        row = getattr(CatalogService(), f"create_{kind}")(
            label=str(label),
            key=request.data.get("key"),
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
    identifiers = None
    if include_identifiers and "identifiers" in request.data:
        identifiers = request.data.get("identifiers")
        if identifiers is not None and not isinstance(identifiers, list):
            return _bad_request("identifiers must be an array of strings")
        if isinstance(identifiers, list) and not all(isinstance(item, str) for item in identifiers):
            return _bad_request("identifiers must be an array of strings")
    try:
        row = getattr(CatalogService(), f"update_{kind}")(
            entry_id=entry_id,
            label=request.data.get("label"),
            key=request.data.get("key"),
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


def _bad_request(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _not_found(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_404_NOT_FOUND)
