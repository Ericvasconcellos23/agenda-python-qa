"""Serviço de lembretes: execute com UM worker. Não depende de IA."""
import logging
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from .models import Task, Notification
logger = logging.getLogger(__name__)

def process_due(now=None):
    now = now or timezone.now()
    created = sent = failed = 0
    for task in Task.objects.filter(completed=False, due_at__lte=now).select_related("user"):
        _, new = Notification.objects.get_or_create(task=task)
        created += int(new)
    eligible = Task.objects.filter(completed=False, due_at__lte=now, email_enabled=True, email_sent_at__isnull=True).filter(Q(next_email_attempt__isnull=True) | Q(next_email_attempt__lte=now)).select_related("user")
    for task in eligible:
        task.email_attempts += 1
        try:
            local = timezone.localtime(task.due_at).strftime("%d/%m/%Y às %H:%M")
            count = send_mail("Lembrete: " + task.title, f"Olá, {task.user.first_name}!\nSua atividade: {task.title}\nData: {local} (São Paulo)\n{task.description}", settings.DEFAULT_FROM_EMAIL, [task.user.email], fail_silently=False)
            if count != 1:
                raise RuntimeError("Backend não confirmou o envio")
        except Exception:
            # Não registrar endereço, senha SMTP ou detalhes pessoais no log.
            logger.warning("Falha no envio da atividade id=%s; haverá nova tentativa", task.pk)
            task.next_email_attempt = now + timedelta(minutes=min(60, 2 ** min(task.email_attempts, 6)))
            failed += 1
        else:
            task.email_sent_at = now
            task.next_email_attempt = None
            sent += 1
        task.save(update_fields=["email_attempts", "email_sent_at", "next_email_attempt"])
    return created, sent, failed
