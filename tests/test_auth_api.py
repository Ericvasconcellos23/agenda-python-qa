"""Testes de autenticação, registro, login e logout com pytest."""
import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestAuthAPI:
    """Testes dos endpoints de autenticação e gestão de usuários."""

    def test_signup_get_renders_form(self, anon_client):
        """GET /cadastro/ deve renderizar o formulário de cadastro com status 200."""
        response = anon_client.get("/cadastro/")
        assert response.status_code == 200
        assert "Criar minha conta" in response.content.decode("utf-8")
        assert 'name="username"' in response.content.decode("utf-8")
        assert 'name="password1"' in response.content.decode("utf-8")

    def test_signup_post_creates_user_and_logs_in(self, anon_client):
        """POST /cadastro/ com dados válidos cria usuário, aplica hash e redireciona."""
        payload = {
            "first_name": "Mariana",
            "username": "MARIANA@Example.COM",
            "password1": "Senha!Segura456",
            "password2": "Senha!Segura456",
        }
        response = anon_client.post("/cadastro/", payload)

        assert response.status_code == 302
        assert response.url == "/"

        # Verifica normalização em minúsculas e hash de senha
        created_user = User.objects.get(username="mariana@example.com")
        assert created_user.email == "mariana@example.com"
        assert created_user.first_name == "Mariana"
        assert created_user.check_password("Senha!Segura456")
        assert created_user.password != "Senha!Segura456"

     
        dashboard_response = anon_client.get("/")
        assert dashboard_response.status_code == 200
        assert "Olá, Mariana." in dashboard_response.content.decode("utf-8")

    def test_signup_duplicate_email_case_insensitive(self, anon_client, user):
        """Tentativa de cadastrar e-mail já existente (mesmo em maiúsculas) deve ser rejeitada."""
        payload = {
            "first_name": "Outra Ana",
            "username": user.username.upper(),
            "password1": "OutraSenha!987",
            "password2": "OutraSenha!987",
        }
        response = anon_client.post("/cadastro/", payload)

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Este e-mail já está cadastrado." in content
        assert User.objects.filter(username__iexact=user.username).count() == 1

    @pytest.mark.parametrize(
        "weak_password,expected_error_substr",
        [
            ("123", "muito curta"),
            ("12345678", "inteiramente numérica"),
            ("password", "muito comum"),
        ],
    )
    def test_signup_weak_password_rejected(self, anon_client, weak_password, expected_error_substr):
        """Formulário deve rejeitar senhas fracas com base nos validadores do Django."""
        payload = {
            "first_name": "Carlos",
            "username": "carlos@example.com",
            "password1": weak_password,
            "password2": weak_password,
        }
        response = anon_client.post("/cadastro/", payload)

        assert response.status_code == 200
        assert not User.objects.filter(username="carlos@example.com").exists()

    def test_signup_password_mismatch(self, anon_client):
        """Divergência entre password1 e password2 deve invalidar o cadastro."""
        payload = {
            "first_name": "Lucas",
            "username": "lucas@example.com",
            "password1": "Senha!Valida123",
            "password2": "OutraSenhaDiferente999",
        }
        response = anon_client.post("/cadastro/", payload)
        assert response.status_code == 200
        assert not User.objects.filter(username="lucas@example.com").exists()

    def test_login_success(self, anon_client, user, user_password):
        """POST /accounts/login/ com credenciais corretas autentica e redireciona."""
        response = anon_client.post(
            "/accounts/login/",
            {"username": user.username, "password": user_password},
        )
        assert response.status_code == 302
        assert response.url == "/"

     
        dashboard = anon_client.get("/")
        assert dashboard.status_code == 200
        assert f"Olá, {user.first_name}." in dashboard.content.decode("utf-8")

    def test_login_invalid_credentials(self, anon_client, user):
        """Login com senha incorreta deve falhar sem autenticar o usuário."""
        response = anon_client.post(
            "/accounts/login/",
            {"username": user.username, "password": "senha_totalmente_errada"},
        )
        assert response.status_code == 200

        dashboard = anon_client.get("/")
        assert dashboard.status_code == 302
        assert "/accounts/login/" in dashboard.url

    def test_logout_terminates_session(self, auth_client):
        """POST /accounts/logout/ encerra a sessão ativa."""
        response = auth_client.post("/accounts/logout/")
        assert response.status_code == 302
        assert response.url == "/accounts/login/"

  
        follow_up = auth_client.get("/")
        assert follow_up.status_code == 302
        assert "/accounts/login/" in follow_up.url

    def test_signup_form_save_commit_false(self):
        """Testa o salvamento do formulário com commit=False sem persistir imediatamente."""
        from lembretes.forms import SignupForm
        form = SignupForm(
            data={
                "first_name": "Fabio",
                "username": "fabio@example.com",
                "password1": "Senha!Valida999",
                "password2": "Senha!Valida999",
            }
        )
        assert form.is_valid()
        user_instance = form.save(commit=False)
        assert user_instance.email == "fabio@example.com"
        assert user_instance.pk is None  # Não gravado no banco ainda
        user_instance.save()
        assert user_instance.pk is not None

    @pytest.mark.parametrize(
        "protected_url",
        [
            "/",
            "/atividade/nova/",
            "/atividade/1/editar/",
        ],
    )
    def test_anonymous_access_redirects_to_login(self, anon_client, protected_url):
        """Rotas protegidas devem redirecionar visitantes não autenticados."""
        response = anon_client.get(protected_url)
        assert response.status_code == 302
        assert "/accounts/login/?next=" in response.url
