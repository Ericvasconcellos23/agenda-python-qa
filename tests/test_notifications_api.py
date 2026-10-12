"""Testes do endpoint de notificações in-app e isolamento de leitura."""
import pytest
from lembretes.models import Notification


@pytest.mark.django_db
class TestNotificationsAPI:
    """Testes dos endpoints de notificações."""

    def test_read_notification_post_marks_as_read(self, auth_client, user, overdue_task):
        """POST /notificacao/<pk>/ler/ marca a notificação como lida com sucesso."""
        notification = Notification.objects.create(task=overdue_task, read=False)

        response = auth_client.post(f"/notificacao/{notification.pk}/ler/")
        assert response.status_code == 302
        assert response.url == "/"

        notification.refresh_from_db()
        assert notification.read is True

    def test_read_notification_get_method_not_allowed(self, auth_client, overdue_task):
        """GET /notificacao/<pk>/ler/ deve ser rejeitado com 405 Method Not Allowed."""
        notification = Notification.objects.create(task=overdue_task)
        response = auth_client.get(f"/notificacao/{notification.pk}/ler/")
        assert response.status_code == 405

    def test_idor_cannot_read_foreign_notification(self, other_client, overdue_task):
        """Usuário B não pode marcar como lida uma notificação pertencente ao Usuário A."""
        notification = Notification.objects.create(task=overdue_task, read=False)
        response = other_client.post(f"/notificacao/{notification.pk}/ler/")

        assert response.status_code == 404
        notification.refresh_from_db()
        assert notification.read is False

    def test_read_nonexistent_notification_returns_404(self, auth_client):
        """Tentativa de marcar como lida uma notificação inexistente retorna 404."""
        response = auth_client.post("/notificacao/999999/ler/")
        assert response.status_code == 404

    def test_dashboard_displays_notification_status(self, auth_client, overdue_task):
        """Verifica a renderização do estado não lido e lido no dashboard."""
        notification = Notification.objects.create(task=overdue_task, read=False)

        # Não lida: exibe botão "Marcar como lida"
        res1 = auth_client.get("/")
        assert "Marcar como lida" in res1.content.decode("utf-8")

        # Marcada como lida: exibe badge "Lida"
        notification.read = True
        notification.save()
        res2 = auth_client.get("/")
        assert "Lida" in res2.content.decode("utf-8")

