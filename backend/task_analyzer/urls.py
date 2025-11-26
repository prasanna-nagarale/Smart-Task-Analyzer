# inside project urls.py
from django.urls import path, include

urlpatterns = [
    # ... other urls ...
    path("api/tasks/", include("tasks.urls")),
]
