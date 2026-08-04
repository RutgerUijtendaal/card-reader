from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.http import FileResponse, HttpResponse
from django.http.response import HttpResponseBase
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.auth_access import can_download_developer_data
from card_reader_api.common.permissions import DeveloperDataAllowed, DeveloperDataManagementAllowed
from card_reader_core.config.settings import settings
from card_reader_core.models import DeveloperDataBuild, DeveloperDataBuildStatus
from card_reader_core.operations.developer_data import (
    DeveloperDataError,
    InvalidDeveloperDataVersion,
    PublishedBundleStore,
)
from card_reader_core.operations.developer_data.schema import DeveloperDataLock, PublishedBundle
from card_reader_core.services.developer_data import (
    DeveloperDataBuildAlreadyActiveError,
    DeveloperDataGrantService,
    queue_developer_data_build,
    recent_developer_data_builds,
)

from .serializers import DeveloperDataCodeExchangeSerializer


class DeveloperDataCurrentView(APIView):
    permission_classes = [DeveloperDataAllowed]

    def get(self, _request: Request) -> Response:
        try:
            bundle = PublishedBundleStore().current()
        except DeveloperDataError as exc:
            return Response(
                {"available": False, "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if bundle is None:
            return Response({"available": False})
        return Response({"available": True, **_bundle_payload(bundle)})


class DeveloperDataGrantView(APIView):
    permission_classes = [DeveloperDataAllowed]

    def post(self, request: Request) -> Response:
        grant = DeveloperDataGrantService().create_code(user=request.user)
        return Response(
            {
                "code": grant.value,
                "expires_at": grant.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class DeveloperDataBuildListView(APIView):
    permission_classes = [DeveloperDataManagementAllowed]

    def get(self, _request: Request) -> Response:
        return Response({"builds": [_build_payload(build) for build in recent_developer_data_builds()]})

    def post(self, request: Request) -> Response:
        try:
            build = queue_developer_data_build(requested_by=request.user)
        except DeveloperDataBuildAlreadyActiveError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(_build_payload(build), status=status.HTTP_201_CREATED)


class DeveloperDataBuildLockView(APIView):
    permission_classes = [DeveloperDataManagementAllowed]

    def get(self, _request: Request, build_id: str) -> HttpResponseBase | Response:
        build = DeveloperDataBuild.objects.filter(id=build_id).first()
        if build is None:
            return Response({"detail": "Developer-data build was not found."}, status=status.HTTP_404_NOT_FOUND)
        if build.status != DeveloperDataBuildStatus.succeeded:
            return Response(
                {"detail": "The developer-data build has not completed successfully."},
                status=status.HTTP_409_CONFLICT,
            )
        if build.format_version is None or not build.sha256:
            return Response(
                {"detail": "The completed developer-data build metadata is incomplete."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        lock = DeveloperDataLock(
            api_base_url=settings.developer_data_public_api_base_url.rstrip("/"),
            bundle_version=build.bundle_version,
            format_version=build.format_version,
            sha256=build.sha256,
        )
        response = HttpResponse(
            content=json.dumps(lock.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            content_type="application/json",
        )
        response["Content-Disposition"] = 'attachment; filename="dev-data.lock.json"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class DeveloperDataGrantExchangeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = DeveloperDataCodeExchangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bundle_version = serializer.validated_data["bundle_version"]
        grant_service = DeveloperDataGrantService()
        if not grant_service.can_exchange_code(code=serializer.validated_data["code"]):
            return Response(
                {"detail": "Bootstrap code is invalid, expired, or already used."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bundle, error_response = _load_bundle(bundle_version)
        if error_response is not None:
            return error_response
        assert bundle is not None
        token = grant_service.exchange_code(
            code=serializer.validated_data["code"],
            bundle_version=bundle.bundle_version,
        )
        if token is None:
            return Response(
                {"detail": "Bootstrap code is invalid, expired, or already used."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "download_token": token.value,
                "expires_at": token.expires_at,
                "bundle": _bundle_payload(bundle),
            }
        )


class DeveloperDataBundleDownloadView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, bundle_version: str) -> HttpResponseBase | Response:
        if not can_download_developer_data(request.user):
            token = _developer_data_token(request)
            if token is None or DeveloperDataGrantService().authorize_token(
                token=token,
                bundle_version=bundle_version,
            ) is None:
                return Response(
                    {"detail": "Active account authentication is required."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        bundle, error_response = _load_bundle(bundle_version)
        if error_response is not None:
            return error_response
        assert bundle is not None

        store = PublishedBundleStore()
        archive_path = store.archive_path(bundle)
        if not settings.is_dev and not settings.developer_data_accel_redirect_prefix.strip():
            return Response(
                {"detail": "Protected developer-data transfer is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = _download_response(archive_path=archive_path, bundle=bundle)
        _apply_download_headers(response, bundle)
        return response


def _load_bundle(bundle_version: str) -> tuple[PublishedBundle | None, Response | None]:
    try:
        bundle = PublishedBundleStore().get(bundle_version)
    except InvalidDeveloperDataVersion:
        return None, Response(
            {"detail": "Developer-data bundle is not published."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except DeveloperDataError as exc:
        return None, Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if bundle is None:
        return None, Response(
            {"detail": "Developer-data bundle is not published."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return bundle, None


def _developer_data_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "").strip()
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "devdata":
        return None
    return parts[1]


def _download_response(*, archive_path: Path, bundle: PublishedBundle) -> HttpResponseBase:
    accel_prefix = settings.developer_data_accel_redirect_prefix.strip()
    if accel_prefix:
        normalized_prefix = f"/{accel_prefix.strip('/')}"
        response = HttpResponse(content_type="application/gzip")
        response["X-Accel-Redirect"] = f"{normalized_prefix}/{bundle.filename}"
        return response
    return FileResponse(archive_path.open("rb"), content_type="application/gzip")


def _apply_download_headers(response: HttpResponseBase, bundle: PublishedBundle) -> None:
    response["Content-Disposition"] = f'attachment; filename="{bundle.filename}"'
    response["Content-Length"] = str(bundle.size_bytes)
    response["Cache-Control"] = "private, no-store"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"


def _bundle_payload(bundle: PublishedBundle) -> dict[str, Any]:
    return {
        "bundle_version": bundle.bundle_version,
        "format_version": bundle.format_version,
        "sha256": bundle.sha256,
        "size_bytes": bundle.size_bytes,
        "created_at": bundle.created_at,
        "download_url": f"/developer-data/bundles/{bundle.bundle_version}/download",
    }


def _build_payload(build: DeveloperDataBuild) -> dict[str, Any]:
    requested_by = build.requested_by.username if build.requested_by is not None else None
    return {
        "id": build.id,
        "bundle_version": build.bundle_version,
        "status": build.status,
        "requested_by": requested_by,
        "created_at": build.created_at,
        "started_at": build.started_at,
        "finished_at": build.finished_at,
        "format_version": build.format_version,
        "sha256": build.sha256 or None,
        "size_bytes": build.size_bytes,
        "error_message": build.error_message or None,
        "lock_download_url": (
            f"/developer-data/builds/{build.id}/lock"
            if build.status == DeveloperDataBuildStatus.succeeded
            else None
        ),
    }
