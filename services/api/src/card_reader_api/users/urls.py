from __future__ import annotations

from django.urls import path

from card_reader_api.access_requests.views import (
    AdminAccessRequestApproveView,
    AdminAccessRequestDeclineView,
    AdminAccessRequestListView,
    AdminAccessRequestSummaryView,
)

from .views import (
    ManagedUserDetailView,
    ManagedUserListCreateView,
    ManagedUserResetPasswordView,
    ManagedUserRestoreView,
)

urlpatterns = [
    path("admin/users", ManagedUserListCreateView.as_view()),
    path("admin/users/<str:user_id>", ManagedUserDetailView.as_view()),
    path("admin/users/<str:user_id>/restore", ManagedUserRestoreView.as_view()),
    path("admin/users/<str:user_id>/reset-password", ManagedUserResetPasswordView.as_view()),
    path("admin/access-requests/summary", AdminAccessRequestSummaryView.as_view()),
    path("admin/access-requests", AdminAccessRequestListView.as_view()),
    path("admin/access-requests/<str:access_request_id>/approve", AdminAccessRequestApproveView.as_view()),
    path("admin/access-requests/<str:access_request_id>/decline", AdminAccessRequestDeclineView.as_view()),
]
