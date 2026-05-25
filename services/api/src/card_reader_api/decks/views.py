from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.auth_access import is_authenticated
from card_reader_api.common.permissions import AuthEnabledOrAuthenticatedAllowed
from card_reader_api.decks.serializers import DeckWriteSerializer, deck_payload, serializer_error
from card_reader_core.services.decks import DeckEntryInput, DeckService, DeckSideboardInput, DeckUpdateInput


def _user_id(request: Request) -> str:
    return str(getattr(request.user, "pk", ""))


class PublicDeckListView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        decks = DeckService().list_public_decks()
        return Response([deck_payload(deck) for deck in decks])


class PublicDeckDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, deck_id: str) -> Response:
        viewer_id = _user_id(request) if is_authenticated(request.user) else None
        deck = DeckService().get_deck_for_viewer(deck_id, viewer_id=viewer_id)
        if deck is None:
            return Response({"detail": "Deck not found"}, status=status.HTTP_404_NOT_FOUND)
        if not deck.is_public and str(getattr(deck.owner, "pk", "")) != viewer_id:
            return Response({"detail": "Deck not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(deck_payload(deck))


class OwnerDeckListCreateView(APIView):
    permission_classes = [AuthEnabledOrAuthenticatedAllowed]

    def get(self, request: Request) -> Response:
        owner_id = _user_id(request)
        decks = DeckService().list_owner_decks(owner_id)
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
                is_public=serializer.validated_data["is_public"],
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
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(deck_payload(deck), status=status.HTTP_201_CREATED)


class OwnerDeckDetailView(APIView):
    permission_classes = [AuthEnabledOrAuthenticatedAllowed]

    def get(self, request: Request, deck_id: str) -> Response:
        deck = DeckService().get_owner_deck(deck_id, _user_id(request))
        if deck is None:
            return Response({"detail": "Deck not found"}, status=status.HTTP_404_NOT_FOUND)
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
                    is_public=serializer.validated_data.get("is_public"),
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
                    update_is_public="is_public" in serializer.validated_data,
                    update_hero_card_id="hero_card_id" in serializer.validated_data,
                    update_entries="entries" in serializer.validated_data,
                    update_sideboards="sideboards" in serializer.validated_data,
                ),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if deck is None:
            return Response({"detail": "Deck not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(deck_payload(deck))

    def delete(self, request: Request, deck_id: str) -> Response:
        deleted = DeckService().delete_owner_deck(deck_id=deck_id, owner_id=_user_id(request))
        if not deleted:
            return Response({"detail": "Deck not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
