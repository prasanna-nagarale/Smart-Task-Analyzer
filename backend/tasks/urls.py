from django.urls import path
from .views import analyze_view, suggest_view

urlpatterns = [
    path("analyze/", analyze_view),
    path("suggest/", suggest_view),
]
