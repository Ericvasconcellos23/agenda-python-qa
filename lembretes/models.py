"""Modelos: atividades e notificações persistidas, sempre pertencentes a um usuário."""
from django.conf import settings
from django.db import models
class Task(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, max_length=2000)
    due_at = models.DateTimeField()
    completed = models.BooleanField(default=False)
    email_enabled = models.BooleanField(default=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    next_email_attempt = models.DateTimeField(null=True, blank=True)
    email_attempts = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ["due_at"]
        indexes = [models.Index(fields=["completed", "due_at"])]
class Notification(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
