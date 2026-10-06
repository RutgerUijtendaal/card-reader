from __future__ import annotations

from django.urls import path

from .views import OperationsOverviewView, OperationsQueueView
from .monitoring import MonitoringView

urlpatterns = [
    path("internal/monitoring", MonitoringView.as_view()),
    path("operations", OperationsOverviewView.as_view()),
    path("operations/queues/<str:queue_key>", OperationsQueueView.as_view()),
]
