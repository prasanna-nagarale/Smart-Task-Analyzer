# inside project urls.py
from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    # ... other urls ...
    path("admin/", admin.site.urls),
    path("api/tasks/", include("tasks.urls")),
]
