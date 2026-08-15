from __future__ import annotations

from typing import cast

from django.http import FileResponse, HttpResponse, HttpResponseNotModified
from django.utils.http import http_date, parse_http_date_safe, quote_etag
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from card_reader_api.cards.tts_sheet_access import validate_tts_sheet_access_token
from card_reader_api.common.auth_access import card_pool_scope_for_user
from card_reader_core.models import PLAYER_CARD_POOL, TtsCardSheet
from card_reader_core.services.tts_card_sheets import TtsCardSheetService, tts_card_sheet_path


class TtsCardSheetImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, sheet_id: str) -> HttpResponse:
        return _sheet_response(request, sheet_id, include_body=True)

    def head(self, request: Request, sheet_id: str) -> HttpResponse:
        return _sheet_response(request, sheet_id, include_body=False)


def _sheet_response(request: Request, sheet_id: str, *, include_body: bool) -> HttpResponse:
    sheet_service = TtsCardSheetService()
    for attempt in range(2):
        sheet = TtsCardSheet.objects.filter(id=sheet_id).first()
        if sheet is None:
            return HttpResponse("TTS card sheet not found.", status=404, content_type="text/plain")
        if not _can_access_sheet(request, sheet):
            return HttpResponse("TTS card sheet not found.", status=404, content_type="text/plain")
        if not sheet_service.ensure_sheet_current(sheet_id):
            break
        sheet = TtsCardSheet.objects.filter(id=sheet_id).first()
        if sheet is None:
            return HttpResponse("TTS card sheet not found.", status=404, content_type="text/plain")
        path = tts_card_sheet_path(sheet_id, sheet.rendered_checksum)
        if sheet.published_at is None or not sheet.rendered_checksum or not path.is_file():
            if attempt == 0 and sheet.rendered_checksum:
                continue
            break

        etag = quote_etag(sheet.rendered_checksum)
        if _request_cache_is_current(
            request,
            etag=etag,
            modified_epoch=int(sheet.published_at.timestamp()),
        ):
            return _apply_sheet_headers(HttpResponseNotModified(), sheet=sheet, etag=etag)

        try:
            if include_body:
                response = cast(
                    HttpResponse,
                    FileResponse(
                        path.open("rb"),
                        content_type="image/webp",
                        as_attachment=False,
                        filename=f"card-reader-sheet-{sheet.sequence}.webp",
                    ),
                )
            else:
                response = HttpResponse(content_type="image/webp")
                response["Content-Length"] = str(path.stat().st_size)
                response["Content-Disposition"] = (
                    f'inline; filename="card-reader-sheet-{sheet.sequence}.webp"'
                )
        except FileNotFoundError:
            continue
        return _apply_sheet_headers(response, sheet=sheet, etag=etag)

    sheet_service.request_render(sheet_id)
    unavailable_response = HttpResponse(
        "TTS card sheet is still being prepared.",
        status=503,
        content_type="text/plain",
    )
    unavailable_response["Retry-After"] = "2"
    return unavailable_response


def _apply_sheet_headers(
    response: HttpResponse,
    *,
    sheet: TtsCardSheet,
    etag: str,
) -> HttpResponse:
    assert sheet.published_at is not None
    response["Cache-Control"] = (
        "public, no-cache" if sheet.card_pool == PLAYER_CARD_POOL else "private, no-cache"
    )
    response["ETag"] = etag
    response["Last-Modified"] = http_date(sheet.published_at.timestamp())
    response["X-Card-Reader-TTS-Sheet-ID"] = str(sheet.id)
    response["X-Card-Reader-TTS-Sheet-Revision"] = str(sheet.rendered_revision)
    return response


def _can_access_sheet(request: Request, sheet: TtsCardSheet) -> bool:
    if sheet.card_pool == PLAYER_CARD_POOL:
        return True
    if card_pool_scope_for_user(request.user).allows_card_pool(sheet.card_pool):
        return True
    token = request.query_params.get("access_token", "")
    return bool(token) and validate_tts_sheet_access_token(
        token,
        sheet_id=str(sheet.id),
        rendered_revision=sheet.rendered_revision,
        rendered_checksum=sheet.rendered_checksum,
    )


def _request_cache_is_current(request: Request, *, etag: str, modified_epoch: int) -> bool:
    requested_etag = request.headers.get("If-None-Match")
    if requested_etag is not None:
        return requested_etag.strip() == etag
    modified_since = request.headers.get("If-Modified-Since")
    if modified_since is None:
        return False
    parsed = parse_http_date_safe(modified_since)
    return parsed is not None and parsed >= modified_epoch


__all__ = ["TtsCardSheetImageView"]
