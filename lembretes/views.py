"""Views: recebem requisições; filtram por dono para impedir acesso cruzado."""
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import SignupForm, TaskForm
from .models import Task, Notification

def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")
    return render(request, "form.html", {"form":form, "title":"Criar minha conta"})

@login_required
def dashboard(request):
    return render(request, "dashboard.html", {"tasks":Task.objects.filter(user=request.user), "notifications":Notification.objects.filter(task__user=request.user).select_related("task").order_by("-created_at")})

@login_required
def create(request):
    form = TaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()
        return redirect("dashboard")
    return render(request, "form.html", {"form":form, "title":"Nova atividade"})

@login_required
def edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user, completed=False)
    form = TaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.email_sent_at = None
        task.next_email_attempt = None
        task.email_attempts = 0
        task.save()
        Notification.objects.filter(task=task).delete()
        return redirect("dashboard")
    return render(request, "form.html", {"form":form, "title":"Editar atividade"})

@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Task, pk=pk, user=request.user).delete()
    return redirect("dashboard")

@login_required
@require_POST
def complete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.completed = True
    task.save(update_fields=["completed"])
    return redirect("dashboard")

@login_required
@require_POST
def read(request, pk):
    item = get_object_or_404(Notification, pk=pk, task__user=request.user)
    item.read = True
    item.save(update_fields=["read"])
    return redirect("dashboard")
