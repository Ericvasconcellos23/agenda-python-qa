from django.urls import path
from django.contrib.auth import views as auth
from lembretes import views
urlpatterns = [path("", views.dashboard, name="dashboard"), path("cadastro/", views.signup, name="signup"), path("accounts/login/", auth.LoginView.as_view(), name="login"), path("accounts/logout/", auth.LogoutView.as_view(), name="logout"), path("atividade/nova/", views.create, name="create"), path("atividade/<int:pk>/editar/", views.edit, name="edit"), path("atividade/<int:pk>/excluir/", views.delete, name="delete"), path("atividade/<int:pk>/concluir/", views.complete, name="complete"), path("notificacao/<int:pk>/ler/", views.read, name="read")]
