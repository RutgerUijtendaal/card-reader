from __future__ import annotations

from django.core import signing


_TTS_SHEET_ACCESS_SALT = "card-reader.tts-card-sheet-access.v1"


def create_tts_sheet_access_token(
    *,
    sheet_id: str,
    rendered_revision: int,
    rendered_checksum: str,
) -> str:
    return signing.dumps(
        {
            "sheet_id": sheet_id,
            "rendered_revision": rendered_revision,
            "rendered_checksum": rendered_checksum,
        },
        salt=_TTS_SHEET_ACCESS_SALT,
        compress=True,
    )


def validate_tts_sheet_access_token(
    token: str,
    *,
    sheet_id: str,
    rendered_revision: int,
    rendered_checksum: str,
) -> bool:
    try:
        payload = signing.loads(token, salt=_TTS_SHEET_ACCESS_SALT)
    except signing.BadSignature:
        return False
    return bool(
        payload
        == {
            "sheet_id": sheet_id,
            "rendered_revision": rendered_revision,
            "rendered_checksum": rendered_checksum,
        }
    )


__all__ = ["create_tts_sheet_access_token", "validate_tts_sheet_access_token"]
