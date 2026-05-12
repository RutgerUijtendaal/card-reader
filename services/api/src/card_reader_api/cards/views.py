from __future__ import annotations

from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.serializers import card_payload, metadata_option, symbol_option
from card_reader_core.services.cards import CardService
from card_reader_core.settings import settings


class CardListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        service = CardService()
        cards = service.list_cards(**_card_filters(request))
        payloads = []
        for row in cards.results:
            payloads.append(
                card_payload(
                    row.version.card,
                    row.version,
                    image_url=f"/cards/{row.version.card_id}/image" if row.image else None,
                    metadata={
                        "keywords": row.keywords,
                        "tags": row.tags,
                        "symbols": row.symbols,
                        "types": row.types,
                    },
                )
            )
        return Response(
            {
                "count": cards.count,
                "next_page": cards.page + 1 if cards.page * cards.page_size < cards.count else None,
                "previous_page": cards.page - 1 if cards.page > 1 else None,
                "page": cards.page,
                "page_size": cards.page_size,
                "results": payloads,
            }
        )


class CardFiltersView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        metadata = CardService().get_filter_metadata()
        return Response(
            {
                "keywords": [metadata_option(row) for row in metadata["keywords"]],
                "tags": [metadata_option(row) for row in metadata["tags"]],
                "symbols": [symbol_option(row) for row in metadata["symbols"]],
                "types": [metadata_option(row) for row in metadata["types"]],
            }
        )


class CardDetailView(APIView):
    def get(self, _request: Request, card_id: str) -> Response:
        service = CardService()
        card, version, image = service.get_card_with_image(card_id)
        if card is None or version is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
        metadata = service.get_card_version_metadata(version.id)
        edit_state = service.get_card_version_edit_state(version)
        return Response(
            card_payload(
                card,
                version,
                image_url=f"/cards/{card.id}/image" if image else None,
                metadata=metadata,
                edit_state=edit_state,
            )
        )


class CardGenerationsView(APIView):
    def get(self, _request: Request, card_id: str) -> Response:
        service = CardService()
        card = service.get_card(card_id)
        if card is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        versions = service.list_card_generations(card_id)
        if not versions:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        payloads = []
        for version in versions:
            image = service.get_card_image(version.id)
            metadata = service.get_card_version_metadata(version.id)
            edit_state = service.get_card_version_edit_state(version)
            payloads.append(
                card_payload(
                    card,
                    version,
                    image_url=f"/cards/{card_id}/versions/{version.id}/image" if image else None,
                    metadata=metadata,
                    edit_state=edit_state,
                )
            )
        return Response(payloads)


class LatestCardVersionUpdateView(APIView):
    def patch(self, request: Request, card_id: str) -> Response:
        try:
            updates = _extract_latest_version_updates(request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        restore_fields = _string_list(request.data.get("restore_fields"))
        restore_metadata_groups = _string_list(request.data.get("restore_metadata_groups"))
        unlock_fields = _string_list(request.data.get("unlock_fields"))
        unlock_metadata_groups = _string_list(request.data.get("unlock_metadata_groups"))

        if not _names_are_valid(restore_fields + unlock_fields, _SCALAR_FIELDS):
            return Response({"detail": "Invalid scalar field name."}, status=status.HTTP_400_BAD_REQUEST)
        if not _names_are_valid(restore_metadata_groups + unlock_metadata_groups, _METADATA_GROUPS):
            return Response({"detail": "Invalid metadata group name."}, status=status.HTTP_400_BAD_REQUEST)

        service = CardService()
        updated = service.update_latest_card_version(
            card_id=card_id,
            updates=updates,
            restore_fields=restore_fields,
            restore_metadata_groups=restore_metadata_groups,
            unlock_fields=unlock_fields,
            unlock_metadata_groups=unlock_metadata_groups,
        )
        if updated is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        card, version = updated
        image = service.get_card_image(version.id)
        metadata = service.get_card_version_metadata(version.id)
        edit_state = service.get_card_version_edit_state(version)
        return Response(
            card_payload(
                card,
                version,
                image_url=f"/cards/{card_id}/versions/{version.id}/image" if image else None,
                metadata=metadata,
                edit_state=edit_state,
            )
        )


class CardImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str) -> FileResponse:
        card, _version, image = CardService().get_card_with_image(card_id)
        if card is None or image is None:
            raise Http404("Card image not found")
        return _file_response(Path(image.stored_path), "Card image file is missing")


class CardVersionImageView(APIView):
    def get(self, _request: Request, card_id: str, version_id: str) -> FileResponse:
        service = CardService()
        if service.get_card(card_id) is None:
            raise Http404("Card not found")
        image = service.get_card_image(version_id)
        if image is None:
            raise Http404("Card image not found")
        return _file_response(Path(image.stored_path), "Card image file is missing")


class SymbolAssetView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, asset_path: str) -> FileResponse:
        symbols_root = settings.storage_root_dir.resolve() / "symbols"
        requested_path = (symbols_root / asset_path).resolve()
        try:
            requested_path.relative_to(symbols_root)
        except ValueError as exc:
            raise Http404("Symbol asset not found") from exc
        return _file_response(requested_path, "Symbol asset not found")


def _card_filters(request: Request) -> dict[str, object]:
    return {
        "query": request.query_params.get("q"),
        "max_confidence": _float_param(request, "max_confidence"),
        "keyword_ids": request.query_params.getlist("keyword_ids") or None,
        "tag_ids": request.query_params.getlist("tag_ids") or None,
        "symbol_ids": request.query_params.getlist("symbol_ids") or None,
        "type_ids": request.query_params.getlist("type_ids") or None,
        "mana_cost": request.query_params.get("mana_cost"),
        "template_id": request.query_params.get("template_id"),
        "attack_min": _int_param(request, "attack_min"),
        "attack_max": _int_param(request, "attack_max"),
        "health_min": _int_param(request, "health_min"),
        "health_max": _int_param(request, "health_max"),
        "page": _int_param(request, "page") or 1,
        "page_size": _int_param(request, "page_size") or 72,
    }


def _float_param(request: Request, name: str) -> float | None:
    value = request.query_params.get(name)
    if value is None or value == "":
        return None
    return float(value)


def _int_param(request: Request, name: str) -> int | None:
    value = request.query_params.get(name)
    if value is None or value == "":
        return None
    return int(value)


def _file_response(path: Path, detail: str) -> FileResponse:
    if not path.exists() or not path.is_file():
        raise Http404(detail)
    return FileResponse(path.open("rb"))


_SCALAR_FIELDS = {"name", "type_line", "mana_cost", "attack", "health", "rules_text"}
_METADATA_GROUPS = {"keywords", "tags", "types", "symbols"}


def _extract_latest_version_updates(request: Request) -> dict[str, object]:
    updates: dict[str, object] = {}
    for field_name in _SCALAR_FIELDS:
        if field_name in request.data:
            value = request.data.get(field_name)
            if field_name == "name" and (not isinstance(value, str) or not value.strip()):
                raise ValueError("name is required")
            updates[field_name] = value
    for field_name in ("keyword_ids", "tag_ids", "type_ids", "symbol_ids"):
        if field_name not in request.data:
            continue
        value = request.data.get(field_name)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{field_name} must be an array of strings")
        updates[field_name] = value
    return updates


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _names_are_valid(values: list[str], allowed: set[str]) -> bool:
    return all(value in allowed for value in values)
