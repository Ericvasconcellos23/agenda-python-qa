"""Formulários validam os dados antes de gravar no banco."""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Task
class SignupForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150)
    username = forms.EmailField(label="E-mail", max_length=150)
    class Meta:
        model = User
        fields = ["first_name", "username", "password1", "password2"]
    def clean_username(self):
        email = self.cleaned_data["username"].lower()
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["username"]
        if commit:
            user.save()
        return user
class TaskForm(forms.ModelForm):
    due_at = forms.DateTimeField(label="Data e hora (São Paulo)", input_formats=["%Y-%m-%dT%H:%M"], widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type":"datetime-local"}))
    class Meta:
        model = Task
        fields = ["title", "description", "due_at", "email_enabled"]
        labels = {"title":"Atividade", "description":"Detalhes", "email_enabled":"Receber também por e-mail"}
    def clean_due_at(self):
        value = self.cleaned_data["due_at"]
        if value <= timezone.now():
            raise forms.ValidationError("Escolha uma data e hora futuras.")
        return value
