"""Fixtures modulares para testes de API e integração com pytest."""
from datetime import timedelta
import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone
from lembretes.models import Task, Notification


@pytest.fixture(autouse=True)
def configure_test_email(settings):
    """Garante que todos os testes usem o backend de e-mail em memória."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def anon_client():
    """Cliente HTTP anônimo (sem autenticação)."""
    return Client()


@pytest.fixture
def user_password():
    """Senha forte padrão para testes de usuário."""
    return "UmaSenha!Forte987"


@pytest.fixture
def user_data(user_password):
    """Dados brutos para cadastro e autenticação."""
    return {
        "first_name": "Ana",
        "username": "ana@example.com",
        "password": user_password,
    }


@pytest.fixture
def user(db, user_data):
    """Usuário padrão cadastrado no banco."""
    return User.objects.create_user(
        username=user_data["username"],
        email=user_data["username"],
        first_name=user_data["first_name"],
        password=user_data["password"],
    )


@pytest.fixture
def other_user(db, user_password):
    """Segundo usuário cadastrado para testes de isolamento (IDOR/BOLA)."""
    return User.objects.create_user(
        username="bia@example.com",
        email="bia@example.com",
        first_name="Bia",
        password=user_password,
    )


@pytest.fixture
def auth_client(user):
    """Cliente HTTP autenticado como usuário padrão."""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def other_client(other_user):
    """Cliente HTTP autenticado como segundo usuário."""
    client = Client()
    client.force_login(other_user)
    return client


@pytest.fixture
def csrf_client(user):
    """Cliente autenticado com verificação de CSRF ativada."""
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    return client


@pytest.fixture
def task_factory(db):
    """Factory flexível para criação de tarefas."""
    def _create_task(
        user,
        title="Atividade de Teste",
        description="Descrição detalhada",
        due_at=None,
        completed=False,
        email_enabled=True,
        **kwargs,
    ):
        if due_at is None:
            due_at = timezone.now() + timedelta(days=1)
        return Task.objects.create(
            user=user,
            title=title,
            description=description,
            due_at=due_at,
            completed=completed,
            email_enabled=email_enabled,
            **kwargs,
        )

    return _create_task


@pytest.fixture
def overdue_task(task_factory, user):
    """Tarefa vencida associada ao usuário padrão."""
    return task_factory(
        user=user,
        title="Tarefa Vencida",
        due_at=timezone.now() - timedelta(minutes=5),
    )


@pytest.fixture
def future_task(task_factory, user):
    """Tarefa futura associada ao usuário padrão."""
    return task_factory(
        user=user,
        title="Tarefa Futura",
        due_at=timezone.now() + timedelta(days=2),
    )

