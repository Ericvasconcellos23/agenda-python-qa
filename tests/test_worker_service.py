"""Testes de resiliência e concorrência do worker e serviços em background."""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from lembretes.models import Notification
from lembretes.services import process_due


@pytest.mark.django_db
class TestWorkerService:
    """Testes do serviço assíncrono de notificações e retentativas de e-mail."""

    def test_process_due_success(self, overdue_task, user):
        """Atividade vencida gera exatamente uma notificação e um e-mail."""
        created, sent, failed = process_due(now=overdue_task.due_at)

        assert created == 1
        assert sent == 1
        assert failed == 0

        overdue_task.refresh_from_db()
        assert overdue_task.email_sent_at is not None
        assert Notification.objects.filter(task=overdue_task).count() == 1

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert user.email in sent_email.to
        assert overdue_task.title in sent_email.subject
        assert user.first_name in sent_email.body

    def test_process_due_idempotency(self, overdue_task):
        """Execuções repetidas do worker para o mesmo instante não duplicam envios."""
        fixed_now = overdue_task.due_at
        r1 = process_due(now=fixed_now)
        assert r1 == (1, 1, 0)

        r2 = process_due(now=fixed_now)
        assert r2 == (0, 0, 0)
        assert len(mail.outbox) == 1
        assert Notification.objects.filter(task=overdue_task).count() == 1

    def test_future_and_completed_tasks_ignored(self, future_task, overdue_task):
        """Tarefas futuras e tarefas já concluídas não disparam alertas."""
        overdue_task.completed = True
        overdue_task.save()

        now = timezone.now()
        created, sent, failed = process_due(now=now)
        assert (created, sent, failed) == (0, 0, 0)
        assert len(mail.outbox) == 0

    def test_email_disabled_creates_notification_only(self, overdue_task):
        """Com email_enabled=False, gera apenas notificação no app e nenhum e-mail."""
        overdue_task.email_enabled = False
        overdue_task.save()

        created, sent, failed = process_due(now=overdue_task.due_at)
        assert created == 1
        assert sent == 0
        assert failed == 0
        assert len(mail.outbox) == 0
        assert Notification.objects.filter(task=overdue_task).exists()

    def test_smtp_failure_exponential_backoff_and_retry(self, overdue_task):
        """Simulação de indisponibilidade de SMTP com cálculo de backoff exponencial."""
        now = overdue_task.due_at

        # 1ª Tentativa: falha de rede/SMTP
        with patch("lembretes.services.send_mail", side_effect=OSError("SMTP Host unreachable")):
            created, sent, failed = process_due(now=now)
            assert created == 1
            assert sent == 0
            assert failed == 1

        overdue_task.refresh_from_db()
        assert overdue_task.email_attempts == 1
        assert overdue_task.email_sent_at is None
        assert overdue_task.next_email_attempt is not None
        # Backoff: 2 ** min(1, 6) = 2 minutos
        expected_retry_min = now + timedelta(minutes=2)
        assert abs((overdue_task.next_email_attempt - expected_retry_min).total_seconds()) < 5

        # 2ª Execução antes do prazo de retentativa: não tenta enviar
        created, sent, failed = process_due(now=now + timedelta(minutes=1))
        assert (created, sent, failed) == (0, 0, 0)

        # 3ª Execução após o prazo de retentativa: sucesso
        created, sent, failed = process_due(now=now + timedelta(minutes=3))
        assert (created, sent, failed) == (0, 1, 0)
        overdue_task.refresh_from_db()
        assert overdue_task.email_sent_at is not None

    def test_smtp_backend_zero_send_treated_as_failure(self, overdue_task):
        """Se o backend retornar 0 envios, deve tratar como falha e agendar retentativa."""
        with patch("lembretes.services.send_mail", return_value=0):
            created, sent, failed = process_due(now=overdue_task.due_at)
            assert failed == 1

        overdue_task.refresh_from_db()
        assert overdue_task.email_sent_at is None
        assert overdue_task.email_attempts == 1

    def test_command_process_reminders_single_execution(self, overdue_task):
        """Execução direta do comando de management sem --loop."""
        stdout = StringIO()
        call_command("process_reminders", stdout=stdout)
        output = stdout.getvalue()
        assert "notificações=1 emails=1 falhas=0" in output

    def test_command_process_reminders_loop_execution(self, overdue_task):
        """Execução com flag --loop interrompida por sinal."""
        stdout = StringIO()
        with patch("lembretes.management.commands.process_reminders.time.sleep", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                call_command("process_reminders", loop=True, stdout=stdout)

        assert Notification.objects.filter(task=overdue_task).exists()

