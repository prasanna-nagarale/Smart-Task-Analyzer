# backend/tasks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("analyze/", views.analyze_view, name="tasks-analyze"),
    path("suggest/", views.suggest_view, name="tasks-suggest"),
]
