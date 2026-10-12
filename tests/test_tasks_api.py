"""Testes de endpoints de tarefas (CRUD, autorização IDOR, validações e CSRF)."""
from datetime import timedelta
import pytest
from django.utils import timezone
from lembretes.models import Task, Notification


@pytest.mark.django_db
class TestTasksAPI:
    """Testes dos endpoints de gerenciamento de atividades."""

    def test_dashboard_lists_owner_tasks_only(self, auth_client, user, other_user, task_factory):
        """O dashboard lista apenas as tarefas do usuário conectado, isolando dados de outros."""
        my_task = task_factory(user=user, title="Minha Tarefa Pessoal")
        foreign_task = task_factory(user=other_user, title="Segredo de Outro Usuario")

        response = auth_client.get("/")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Minha Tarefa Pessoal" in content
        assert "Segredo de Outro Usuario" not in content

    def test_create_task_get_renders_form(self, auth_client):
        """GET /atividade/nova/ deve renderizar o formulário com status 200."""
        response = auth_client.get("/atividade/nova/")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Nova atividade" in content
        assert 'name="title"' in content
        assert 'name="due_at"' in content
        assert 'name="email_enabled"' in content

    def test_create_task_post_success(self, auth_client, user):
        """POST /atividade/nova/ com payload válido deve associar o usuário da sessão e salvar."""
        future_dt = timezone.localtime(timezone.now() + timedelta(days=2)).replace(second=0, microsecond=0)
        payload = {
            "title": "Apresentação de QA",
            "description": "Demonstrar suíte de testes automatizados",
            "due_at": future_dt.strftime("%Y-%m-%dT%H:%M"),
            "email_enabled": "on",
        }
        response = auth_client.post("/atividade/nova/", payload)

        assert response.status_code == 302
        assert response.url == "/"

        task = Task.objects.get(title="Apresentação de QA")
        assert task.user == user
        assert task.due_at == future_dt
        assert task.completed is False
        assert task.email_enabled is True

    def test_create_task_past_date_rejected(self, auth_client):
        """Criação com data passada deve falhar com mensagem de validação."""
        past_dt = timezone.localtime(timezone.now() - timedelta(hours=2))
        payload = {
            "title": "Atividade no Passado",
            "due_at": past_dt.strftime("%Y-%m-%dT%H:%M"),
        }
        response = auth_client.post("/atividade/nova/", payload)

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Escolha uma data e hora futuras." in content
        assert not Task.objects.filter(title="Atividade no Passado").exists()

    @pytest.mark.parametrize(
        "title_length,should_succeed",
        [
            (150, True),   # Limite exato de max_length=150
            (151, False),  # Ultrapassa o limite de caracteres
        ],
    )
    def test_create_task_title_boundary(self, auth_client, title_length, should_succeed):
        """Testa o valor limite (boundary testing) para o tamanho do título."""
        future_dt = timezone.localtime(timezone.now() + timedelta(days=1))
        title = "T" * title_length
        payload = {
            "title": title,
            "due_at": future_dt.strftime("%Y-%m-%dT%H:%M"),
        }
        response = auth_client.post("/atividade/nova/", payload)

        if should_succeed:
            assert response.status_code == 302
            assert Task.objects.filter(title=title).exists()
        else:
            assert response.status_code == 200
            assert not Task.objects.filter(title=title).exists()

    def test_edit_task_get_renders_form(self, auth_client, user, task_factory):
        """GET /atividade/<pk>/editar/ renderiza o formulário com dados pré-preenchidos."""
        task = task_factory(user=user, title="Tarefa Original")
        response = auth_client.get(f"/atividade/{task.pk}/editar/")

        assert response.status_code == 200
        assert "Editar atividade" in response.content.decode("utf-8")
        assert "Tarefa Original" in response.content.decode("utf-8")

    def test_edit_task_post_resets_reminders_and_removes_old_notification(
        self, auth_client, user, overdue_task
    ):
        """Ao reagendar tarefa, zera status de e-mail e remove notificação in-app antiga."""

        Notification.objects.create(task=overdue_task)
        overdue_task.email_sent_at = timezone.now()
        overdue_task.email_attempts = 2
        overdue_task.next_email_attempt = timezone.now() + timedelta(minutes=10)
        overdue_task.save()

        new_future_dt = timezone.localtime(timezone.now() + timedelta(days=3))
        payload = {
            "title": "Tarefa Reagendada",
            "description": "Nova data",
            "due_at": new_future_dt.strftime("%Y-%m-%dT%H:%M"),
            "email_enabled": "on",
        }
        response = auth_client.post(f"/atividade/{overdue_task.pk}/editar/", payload)

        assert response.status_code == 302
        overdue_task.refresh_from_db()
        assert overdue_task.title == "Tarefa Reagendada"
        assert overdue_task.email_sent_at is None
        assert overdue_task.next_email_attempt is None
        assert overdue_task.email_attempts == 0
        assert not Notification.objects.filter(task=overdue_task).exists()

    def test_edit_completed_task_returns_404(self, auth_client, user, task_factory):
        """Tarefas já concluídas não podem ser editadas (devem retornar 404)."""
        completed_task = task_factory(user=user, title="Já Concluída", completed=True)
        response = auth_client.get(f"/atividade/{completed_task.pk}/editar/")
        assert response.status_code == 404

    def test_complete_task_post(self, auth_client, user, task_factory):
        """POST /atividade/<pk>/concluir/ marca a atividade como completed=True."""
        task = task_factory(user=user, title="Para Concluir", completed=False)
        response = auth_client.post(f"/atividade/{task.pk}/concluir/")

        assert response.status_code == 302
        task.refresh_from_db()
        assert task.completed is True

    def test_delete_task_post_cascades_notification(self, auth_client, user, overdue_task):
        """POST /atividade/<pk>/excluir/ remove a tarefa e apaga notificação associada."""
        Notification.objects.create(task=overdue_task)
        response = auth_client.post(f"/atividade/{overdue_task.pk}/excluir/")

        assert response.status_code == 302
        assert not Task.objects.filter(pk=overdue_task.pk).exists()
        assert not Notification.objects.filter(task_id=overdue_task.pk).exists()

    # --- Testes de Autorização / IDOR ---

    @pytest.mark.parametrize("action", ["editar/", "excluir/", "concluir/"])
    def test_idor_cannot_mutate_foreign_task(self, other_client, user, task_factory, action):
        """Usuário B não tem permissão para alterar ou excluir tarefas do Usuário A (404 Not Found)."""
        task_user_a = task_factory(user=user, title="Tarefa Confidencial de A")
        response = other_client.post(f"/atividade/{task_user_a.pk}/{action}")
        assert response.status_code == 404

    def test_idor_cannot_view_foreign_edit_form(self, other_client, user, task_factory):
        """Usuário B não pode abrir a tela de edição da tarefa do Usuário A."""
        task_user_a = task_factory(user=user, title="Tarefa de A")
        response = other_client.get(f"/atividade/{task_user_a.pk}/editar/")
        assert response.status_code == 404

    def test_mutate_nonexistent_task_returns_404(self, auth_client):
        """Tentativa de mutação em ID inexistente deve retornar 404."""
        response = auth_client.post("/atividade/999999/concluir/")
        assert response.status_code == 404

    # --- Restrições de Métodos HTTP e CSRF ---

    @pytest.mark.parametrize("action", ["excluir/", "concluir/"])
    def test_http_method_get_not_allowed_on_mutations(self, auth_client, user, task_factory, action):
        """Ações mutativas devem rejeitar requisições GET com 405 Method Not Allowed."""
        task = task_factory(user=user, title="Tarefa Teste")
        response = auth_client.get(f"/atividade/{task.pk}/{action}")
        assert response.status_code == 405

    def test_csrf_protection_enforced(self, csrf_client, user, task_factory):
        """Requisições POST sem token CSRF válido devem ser rejeitadas com 403 Forbidden."""
        task = task_factory(user=user, title="Tarefa CSRF")
        response = csrf_client.post(f"/atividade/{task.pk}/excluir/")
        assert response.status_code == 403

