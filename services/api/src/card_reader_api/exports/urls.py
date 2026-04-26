from __future__ import annotations

from django.urls import path

from .views import ExportCsvView

urlpatterns = [path("exports/csv", ExportCsvView.as_view())]
