from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.responses import bad_request, not_found, serializer_error
from card_reader_api.deck_tags.serializers import (
    DeckTagSuggestionAcceptSerializer,
    DeckTagWriteSerializer,
    deck_tag_detail_payload,
    deck_tag_payload,
    deck_tag_suggestion_detail_payload,
    deck_tag_suggestion_payload,
)
from card_reader_core.services.deck_tags import DeckTagService


class DeckTagCatalogView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        catalog = DeckTagService().list_catalog()
        return Response(
            {
                "roles": [deck_tag_payload(tag) for tag in catalog["roles"]],
                "types": [deck_tag_payload(tag) for tag in catalog["types"]],
            }
        )


class AdminDeckTagCatalogView(APIView):
    def get(self, _request: Request) -> Response:
        service = DeckTagService()
        catalog = service.list_admin_catalog()
        return Response(
            {
                "roles": [deck_tag_payload(tag) for tag in catalog["roles"]],
                "types": [deck_tag_payload(tag) for tag in catalog["types"]],
                "suggested_types": [deck_tag_suggestion_payload(suggestion) for suggestion in catalog["suggested_types"]],
            }
        )

    def post(self, request: Request) -> Response:
        serializer = DeckTagWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            tag = DeckTagService().create_tag(
                kind=serializer.validated_data["kind"],
                label=serializer.validated_data["label"],
                key=serializer.validated_data.get("key"),
            )
        except ValueError as exc:
            return bad_request(str(exc))
        return Response(deck_tag_payload(tag), status=status.HTTP_201_CREATED)


class AdminDeckTagDetailView(APIView):
    def get(self, _request: Request, tag_id: str) -> Response:
        detail = DeckTagService().get_tag_detail(tag_id=tag_id)
        if detail is None:
            return not_found("Deck tag not found")
        return Response(deck_tag_detail_payload(detail))

    def patch(self, request: Request, tag_id: str) -> Response:
        serializer = DeckTagWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            tag = DeckTagService().update_tag(
                tag_id=tag_id,
                kind=serializer.validated_data.get("kind"),
                label=serializer.validated_data.get("label"),
                key=serializer.validated_data.get("key") if "key" in serializer.validated_data else None,
            )
        except ValueError as exc:
            return bad_request(str(exc))
        if tag is None:
            return not_found("Deck tag not found")
        return Response(deck_tag_payload(tag))

    def delete(self, _request: Request, tag_id: str) -> Response:
        if not DeckTagService().delete_tag(tag_id=tag_id):
            return not_found("Deck tag not found")
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminDeckTagSuggestionDetailView(APIView):
    def get(self, _request: Request, suggestion_id: str) -> Response:
        detail = DeckTagService().get_suggestion_detail(suggestion_id=suggestion_id)
        if detail is None:
            return not_found("Deck tag suggestion not found")
        return Response(deck_tag_suggestion_detail_payload(detail))


class AdminDeckTagSuggestionAcceptView(APIView):
    def post(self, request: Request, suggestion_id: str) -> Response:
        serializer = DeckTagSuggestionAcceptSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        service = DeckTagService()
        try:
            if serializer.validated_data.get("target_id"):
                suggestion = service.accept_suggestion_to_existing(
                    suggestion_id=suggestion_id,
                    target_id=serializer.validated_data["target_id"],
                )
            else:
                suggestion = service.accept_suggestion_as_new(
                    suggestion_id=suggestion_id,
                    label=serializer.validated_data.get("label"),
                    key=serializer.validated_data.get("key"),
                )
        except ValueError as exc:
            return bad_request(str(exc))
        if suggestion is None:
            return not_found("Deck tag suggestion not found")
        detail = service.get_suggestion_detail(suggestion_id=suggestion.id)
        if detail is None:
            return not_found("Deck tag suggestion not found")
        return Response(deck_tag_suggestion_detail_payload(detail))


class AdminDeckTagSuggestionRejectView(APIView):
    def post(self, _request: Request, suggestion_id: str) -> Response:
        service = DeckTagService()
        try:
            suggestion = service.reject_suggestion(suggestion_id=suggestion_id)
        except ValueError as exc:
            return bad_request(str(exc))
        if suggestion is None:
            return not_found("Deck tag suggestion not found")
        detail = service.get_suggestion_detail(suggestion_id=suggestion.id)
        if detail is None:
            return not_found("Deck tag suggestion not found")
        return Response(deck_tag_suggestion_detail_payload(detail))


class AdminDeckTagSuggestionReopenView(APIView):
    def post(self, _request: Request, suggestion_id: str) -> Response:
        service = DeckTagService()
        try:
            suggestion = service.reopen_suggestion(suggestion_id=suggestion_id)
        except ValueError as exc:
            return bad_request(str(exc))
        if suggestion is None:
            return not_found("Deck tag suggestion not found")
        detail = service.get_suggestion_detail(suggestion_id=suggestion.id)
        if detail is None:
            return not_found("Deck tag suggestion not found")
        return Response(deck_tag_suggestion_detail_payload(detail))
