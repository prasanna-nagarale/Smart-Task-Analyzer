# backend/tasks/models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField  # JSONField available in Django 3.1+ as models.JSONField

try:
    JSONFieldModel = models.JSONField
except Exception:
    from django.contrib.postgres.fields import JSONField as JSONFieldModel

class Task(models.Model):
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.FloatField(default=1.0)
    importance = models.IntegerField(default=5)
    # dependencies stored as list of task ids (strings) for simplicity
    dependencies = JSONFieldModel(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (importance={self.importance})"
