from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet


class ManagedUserService:
    def list_users(self, *, include_inactive: bool = False) -> tuple[list[AbstractBaseUser], list[AbstractBaseUser]]:
        managed_queryset = self._managed_user_queryset()
        unmanaged_queryset = self._unmanaged_user_queryset()
        if not include_inactive:
            managed_queryset = managed_queryset.filter(is_active=True)
            unmanaged_queryset = unmanaged_queryset.filter(is_active=True)
        return (
            list(managed_queryset.order_by("username")),
            list(unmanaged_queryset.order_by("username")),
        )

    def create_user(self, *, username: str) -> AbstractBaseUser:
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("Username is required.")
        if self._user_model().objects.filter(username=normalized_username).exists():
            raise ValueError("A user with that username already exists.")

        user = self._user_model().objects.create_user(username=normalized_username)
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        user.set_unusable_password()
        user.save(update_fields=["is_staff", "is_superuser", "is_active", "password"])
        return user

    def deactivate_user(self, *, user_id: str) -> AbstractBaseUser | None:
        user = self._managed_user_by_id(user_id)
        if user is None:
            return None
        if not user.is_active:
            return user
        user.is_active = False
        user.save(update_fields=["is_active"])
        return user

    def restore_user(self, *, user_id: str) -> AbstractBaseUser | None:
        user = self._managed_user_by_id(user_id)
        if user is None:
            return None
        if user.is_active:
            return user
        user.is_active = True
        user.save(update_fields=["is_active"])
        return user

    def get_managed_user(self, *, user_id: str) -> AbstractBaseUser | None:
        return self._managed_user_by_id(user_id)

    def _managed_user_by_id(self, user_id: str) -> AbstractBaseUser | None:
        try:
            return self._managed_user_queryset().get(pk=user_id)
        except self._user_model().DoesNotExist:
            return None

    def _managed_user_queryset(self) -> QuerySet[AbstractBaseUser]:
        return self._user_model().objects.filter(is_staff=False, is_superuser=False)

    def _unmanaged_user_queryset(self) -> QuerySet[AbstractBaseUser]:
        return self._user_model().objects.filter(is_staff=True) | self._user_model().objects.filter(
            is_superuser=True
        )

    def _user_model(self):
        return get_user_model()
