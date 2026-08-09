from __future__ import annotations

from django.urls import path

from .views import OperationsOverviewView, OperationsQueueView

urlpatterns = [
    path("operations", OperationsOverviewView.as_view()),
    path("operations/queues/<str:queue_key>", OperationsQueueView.as_view()),
]
