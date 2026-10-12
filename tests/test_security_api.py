"""Testes de segurança aplicacionais (XSS, SQL Injection, CSRF, configurações de produção)."""
import os
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client
from lembretes.models import Task


@pytest.mark.django_db
class TestSecurityAPI:
    """Testes de segurança, sanitização e configurações de ambiente."""

    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('xss')</script>",
            '<img src="x" onerror="alert(1)">',
            "<svg/onload=alert('svg')>",
        ],
    )
    def test_xss_protection_in_templates(self, auth_client, user, task_factory, xss_payload):
        """Conteúdo malicioso injetado no título ou descrição deve ser escapado pelo Django."""
        task_factory(
            user=user,
            title=f"Aviso {xss_payload}",
            description=f"Detalhe {xss_payload}",
        )
        response = auth_client.get("/")
        assert response.status_code == 200
        content = response.content.decode("utf-8")

        
        assert xss_payload not in content
        assert "&lt;" in content
        assert "&gt;" in content

    def test_sql_injection_resilience_in_orm(self, auth_client, user, task_factory):
        """Strings com payloads de injeção SQL devem ser tratadas como texto literal pelo ORM."""
        sqli_payload = "'; DROP TABLE lembretes_task; --"
        task = task_factory(user=user, title=sqli_payload)

        response = auth_client.get("/")
        assert response.status_code == 200
        assert Task.objects.filter(pk=task.pk, title=sqli_payload).exists()

    def test_csrf_protection_on_all_post_endpoints(self, csrf_client, overdue_task):
        """Todos os endpoints mutativos rejeitam POST sem token CSRF."""
        endpoints = [
            f"/atividade/{overdue_task.pk}/concluir/",
            f"/atividade/{overdue_task.pk}/excluir/",
        ]
        for endpoint in endpoints:
            response = csrf_client.post(endpoint)
            assert response.status_code == 403, f"Endpoint {endpoint} deveria bloquear sem CSRF"

    def test_settings_secret_key_production_check(self):
        """Em produção (DEBUG=False), o uso da SECRET_KEY default deve lançar exceção."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("DEBUG", "0")
            mp.setenv("SECRET_KEY", "somente-desenvolvimento-nao-usar-em-producao")
            # Ao importar ou recarregar as configurações sob essas variáveis:
            with pytest.raises(ImproperlyConfigured, match="Defina SECRET_KEY em produção"):
                import importlib
                import config.settings
                importlib.reload(config.settings)

