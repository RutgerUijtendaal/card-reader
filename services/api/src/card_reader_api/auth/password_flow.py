from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


@dataclass(frozen=True)
class PasswordSetupLink:
    uid: str
    token: str
    setup_url: str
    expires_in_seconds: int


@dataclass(frozen=True)
class PasswordSetupValidation:
    valid: bool
    username: str | None = None
    detail: str | None = None


class PasswordSetupService:
    def build_setup_link(self, user: AbstractBaseUser, request: HttpRequest) -> PasswordSetupLink:
        uid = urlsafe_base64_encode(force_bytes(getattr(user, "pk")))
        token = default_token_generator.make_token(user)
        setup_path = f"/password-setup?uid={quote(uid)}&token={quote(token)}"
        return PasswordSetupLink(
            uid=uid,
            token=token,
            setup_url=_build_frontend_url(request, setup_path),
            expires_in_seconds=int(getattr(settings, "PASSWORD_RESET_TIMEOUT", 259200)),
        )

    def validate(self, uid: str, token: str) -> PasswordSetupValidation:
        user = _resolve_user(uid)
        if user is None:
            return PasswordSetupValidation(valid=False, detail="Invalid password setup link.")
        if not getattr(user, "is_active", False):
            return PasswordSetupValidation(valid=False, detail="This account is inactive.")
        if not default_token_generator.check_token(user, token):
            return PasswordSetupValidation(valid=False, detail="Invalid or expired password setup link.")
        return PasswordSetupValidation(valid=True, username=user.get_username())

    def set_password(self, *, uid: str, token: str, password: str) -> AbstractBaseUser:
        user = _resolve_user(uid)
        if user is None or not getattr(user, "is_active", False):
            raise ValueError("Invalid password setup link.")
        if not default_token_generator.check_token(user, token):
            raise ValueError("Invalid or expired password setup link.")
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise ValueError(" ".join(exc.messages)) from exc
        user.set_password(password)
        user.save(update_fields=["password"])
        return user


def _resolve_user(uid: str) -> AbstractBaseUser | None:
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError, OverflowError):
        return None

    user_model = get_user_model()
    try:
        return user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        return None


def _build_frontend_url(request: HttpRequest, path: str) -> str:
    origin = request.headers.get("Origin", "").strip()
    if origin.startswith(("http://", "https://")):
        return f"{origin.rstrip('/')}{path}"
    return request.build_absolute_uri(path)
