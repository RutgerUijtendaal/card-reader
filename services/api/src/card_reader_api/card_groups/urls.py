from __future__ import annotations

from django.urls import path

from .views import PublicCardGroupDetailView, StaffCardGroupDetailView, StaffCardGroupListCreateView

urlpatterns = [
    path("card-groups/<str:group_id>", PublicCardGroupDetailView.as_view()),
    path("admin/card-groups", StaffCardGroupListCreateView.as_view()),
    path("admin/card-groups/<str:group_id>", StaffCardGroupDetailView.as_view()),
]
