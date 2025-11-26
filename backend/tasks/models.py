# backend/tasks/models.py
from django.db import models

class Task(models.Model):
    """
    Task model for storing task information.
    Note: This model is optional for the assignment since we're processing
    tasks in-memory via API. Included for future scalability.
    """
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.FloatField(default=1.0)
    importance = models.IntegerField(default=5)
    
    # Store dependencies as JSON - works with both SQLite and PostgreSQL
    dependencies = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    def __str__(self):
        return f"{self.title} (importance={self.importance}, due={self.due_date})"

    def clean(self):
        """Validate model data"""
        from django.core.exceptions import ValidationError
        
        if self.importance < 1 or self.importance > 10:
            raise ValidationError('Importance must be between 1 and 10')
        
        if self.estimated_hours < 0:
            raise ValidationError('Estimated hours cannot be negative')