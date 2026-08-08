from __future__ import annotations

from django.urls import path

from .views import OperationsOverviewView

urlpatterns = [
    path("operations", OperationsOverviewView.as_view()),
]
