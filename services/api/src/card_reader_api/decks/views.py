from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.auth_access import is_authenticated
from card_reader_api.common.permissions import AuthEnabledOrAuthenticatedAllowed
from card_reader_api.common.responses import bad_request, not_found, serializer_error
from card_reader_api.decks.serializers import (
    DeckListQuerySerializer,
    DeckWriteSerializer,
    deck_payload,
    deck_summary_payload,
)
from card_reader_core.services.decks import (
    DeckEntryInput,
    DeckService,
    DeckSideboardInput,
    DeckUpdateInput,
    deck_building_rules_metadata_json,
)


def _user_id(request: Request) -> str:
    return str(getattr(request.user, "pk", ""))


class DeckRulesMetadataView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        return Response(deck_building_rules_metadata_json())


class PublicDeckListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        serializer = DeckListQuerySerializer(
            data={
                "hero_q": request.query_params.get("hero_q"),
                "q": request.query_params.get("q"),
                "view": request.query_params.get("view"),
                "author_q": request.query_params.get("author_q"),
                "card_q": request.query_params.get("card_q"),
                "affinity_symbol_ids": request.query_params.getlist("affinity_symbol_ids"),
                "affinity_symbol_exclude_ids": request.query_params.getlist("affinity_symbol_exclude_ids"),
                "affinity_symbol_match": request.query_params.get("affinity_symbol_match"),
            }
        )
        if not serializer.is_valid():
            return serializer_error(serializer)
        filters = serializer.validated_list_filters()
        service = DeckService()
        list_decks = service.list_public_deck_summaries if serializer.wants_summary() else service.list_public_decks
        decks = list_decks(
            search_query=filters["search_query"],
            hero_query=filters["hero_query"],
            author_query=filters["author_query"],
            card_query=filters["card_query"],
            affinity_symbol_ids=filters["affinity_symbol_ids"],
            affinity_symbol_exclude_ids=filters["affinity_symbol_exclude_ids"],
            affinity_symbol_match=filters["affinity_symbol_match"],
        )
        if serializer.wants_summary():
            return Response([deck_summary_payload(deck) for deck in decks])
        return Response([deck_payload(deck) for deck in decks])


class PublicDeckDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, deck_id: str) -> Response:
        viewer_id = _user_id(request) if is_authenticated(request.user) else None
        deck = DeckService().get_deck_for_viewer(deck_id, viewer_id=viewer_id)
        if deck is None:
            return not_found("Deck not found")
        return Response(deck_payload(deck))


class OwnerDeckListCreateView(APIView):
    permission_classes = [AuthEnabledOrAuthenticatedAllowed]

    def get(self, request: Request) -> Response:
        serializer = DeckListQuerySerializer(
            data={
                "hero_q": request.query_params.get("hero_q"),
                "q": request.query_params.get("q"),
                "view": request.query_params.get("view"),
                "author_q": request.query_params.get("author_q"),
                "card_q": request.query_params.get("card_q"),
                "affinity_symbol_ids": request.query_params.getlist("affinity_symbol_ids"),
                "affinity_symbol_exclude_ids": request.query_params.getlist("affinity_symbol_exclude_ids"),
                "affinity_symbol_match": request.query_params.get("affinity_symbol_match"),
            }
        )
        if not serializer.is_valid():
            return serializer_error(serializer)
        filters = serializer.validated_list_filters()
        owner_id = _user_id(request)
        service = DeckService()
        list_decks = service.list_owner_deck_summaries if serializer.wants_summary() else service.list_owner_decks
        decks = list_decks(
            owner_id,
            search_query=filters["search_query"],
            hero_query=filters["hero_query"],
            card_query=filters["card_query"],
            affinity_symbol_ids=filters["affinity_symbol_ids"],
            affinity_symbol_exclude_ids=filters["affinity_symbol_exclude_ids"],
            affinity_symbol_match=filters["affinity_symbol_match"],
        )
        if serializer.wants_summary():
            return Response([deck_summary_payload(deck) for deck in decks])
        return Response([deck_payload(deck) for deck in decks])

    def post(self, request: Request) -> Response:
        serializer = DeckWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            deck = DeckService().create_owner_deck(
                owner_id=_user_id(request),
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description"),
                visibility=serializer.validated_data["visibility"],
                hero_card_id=serializer.validated_data["hero_card_id"],
                entries=[DeckEntryInput(**entry) for entry in serializer.validated_data["entries"]],
                sideboards=[
                    DeckSideboardInput(
                        name=sideboard["name"],
                        entries=[DeckEntryInput(**entry) for entry in sideboard["entries"]],
                    )
                    for sideboard in serializer.validated_data.get("sideboards", [])
                ],
            )
        except ValueError as exc:
            return bad_request(str(exc))
        return Response(deck_payload(deck), status=status.HTTP_201_CREATED)


class OwnerDeckDetailView(APIView):
    permission_classes = [AuthEnabledOrAuthenticatedAllowed]

    def get(self, request: Request, deck_id: str) -> Response:
        deck = DeckService().get_owner_deck(deck_id, _user_id(request))
        if deck is None:
            return not_found("Deck not found")
        return Response(deck_payload(deck))

    def patch(self, request: Request, deck_id: str) -> Response:
        serializer = DeckWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            deck = DeckService().update_owner_deck(
                deck_id=deck_id,
                owner_id=_user_id(request),
                updates=DeckUpdateInput(
                    name=serializer.validated_data.get("name"),
                    description=serializer.validated_data.get("description"),
                    visibility=serializer.validated_data.get("visibility"),
                    hero_card_id=serializer.validated_data.get("hero_card_id"),
                    entries=(
                        [DeckEntryInput(**entry) for entry in serializer.validated_data["entries"]]
                        if "entries" in serializer.validated_data
                        else None
                    ),
                    sideboards=(
                        [
                            DeckSideboardInput(
                                name=sideboard["name"],
                                entries=[DeckEntryInput(**entry) for entry in sideboard["entries"]],
                            )
                            for sideboard in serializer.validated_data["sideboards"]
                        ]
                        if "sideboards" in serializer.validated_data
                        else None
                    ),
                    update_name="name" in serializer.validated_data,
                    update_description="description" in serializer.validated_data,
                    update_visibility="visibility" in serializer.validated_data,
                    update_hero_card_id="hero_card_id" in serializer.validated_data,
                    update_entries="entries" in serializer.validated_data,
                    update_sideboards="sideboards" in serializer.validated_data,
                ),
            )
        except ValueError as exc:
            return bad_request(str(exc))
        if deck is None:
            return not_found("Deck not found")
        return Response(deck_payload(deck))

    def delete(self, request: Request, deck_id: str) -> Response:
        deleted = DeckService().delete_owner_deck(deck_id=deck_id, owner_id=_user_id(request))
        if not deleted:
            return not_found("Deck not found")
        return Response(status=status.HTTP_204_NO_CONTENT)
