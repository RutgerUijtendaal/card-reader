from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from card_reader_api.common.views import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", HealthView.as_view()),
    path("auth/", include("card_reader_api.auth.urls")),
    path("", include("card_reader_api.imports.urls")),
    path("", include("card_reader_api.cards.urls")),
    path("", include("card_reader_api.catalog.urls")),
    path("", include("card_reader_api.templates.urls")),
    path("", include("card_reader_api.exports.urls")),
    path("", include("card_reader_api.maintenance.urls")),
]
