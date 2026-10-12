from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from .models import Task, Notification
from .forms import TaskForm, SignupForm
from .services import process_due

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AgendaTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('ana@example.com',email='ana@example.com',password='Senha!Teste987',first_name='Ana')
        self.other=User.objects.create_user('bia@example.com',email='bia@example.com',password='Senha!Teste987')
        self.client.force_login(self.user)
        self.now=timezone.now()
        self.task=Task.objects.create(user=self.user,title='Consulta',due_at=self.now-timedelta(minutes=1))
    def signup_data(self,email='LUANA@example.com',password='UmaSenha!Forte762'):
        return dict(first_name='Luana',username=email,password1=password,password2=password)
    def test_signup_hashed_normalized(self):
        self.client.logout()
        self.assertEqual(self.client.post('/cadastro/',self.signup_data()).status_code,302)
        user=User.objects.get(username='luana@example.com')
        self.assertEqual(user.email,user.username)
        self.assertTrue(user.check_password('UmaSenha!Forte762'))
        self.assertNotEqual(user.password,'UmaSenha!Forte762')
    def test_duplicate_email(self):
        self.assertFalse(SignupForm(data=self.signup_data('ANA@example.com')).is_valid())
    def test_weak_password(self):
        self.assertFalse(SignupForm(data=self.signup_data(password='123')).is_valid())
    def test_login_logout(self):
        self.client.logout()
        self.assertEqual(self.client.post('/accounts/login/',dict(username=self.user.username,password='errada')).status_code,200)
        self.assertEqual(self.client.post('/accounts/login/',dict(username=self.user.username,password='Senha!Teste987')).status_code,302)
        self.assertEqual(self.client.post('/accounts/logout/').status_code,302)
        self.assertEqual(self.client.get('/').status_code,302)
    def test_anonymous_blocked(self):
        self.client.logout();self.assertEqual(self.client.get('/atividade/nova/').status_code,302)
    def test_past_invalid(self):
        form=TaskForm(data=dict(title='Teste',due_at=timezone.localtime(self.now-timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')))
        self.assertFalse(form.is_valid());self.assertIn('due_at',form.errors)
    def test_create_timezone(self):
        dt=timezone.localtime(self.now+timedelta(days=1)).replace(second=0,microsecond=0)
        self.assertEqual(self.client.post('/atividade/nova/',dict(title='Estudar',due_at=dt.strftime('%Y-%m-%dT%H:%M'),email_enabled='on')).status_code,302)
        task=Task.objects.get(title='Estudar');self.assertEqual(task.due_at,dt);self.assertEqual(task.user,self.user)
    def test_isolation(self):
        foreign=Task.objects.create(user=self.other,title='Segredo',due_at=self.now)
        self.assertNotContains(self.client.get('/'),'Segredo')
        for action in ['editar','excluir','concluir']:
            self.assertEqual(self.client.post(f'/atividade/{foreign.pk}/{action}/').status_code,404)
    def test_get_cannot_delete(self):
        self.assertEqual(self.client.get(f'/atividade/{self.task.pk}/excluir/').status_code,405)
    def test_csrf(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post(f'/atividade/{self.task.pk}/excluir/').status_code,403)
    def test_due_no_repeat(self):
        self.assertEqual(process_due(self.now),(1,1,0));self.assertEqual(process_due(self.now),(0,0,0))
        self.assertEqual(len(mail.outbox),1);self.assertEqual(mail.outbox[0].to,[self.user.email])
    def test_future(self):
        self.task.due_at=self.now+timedelta(hours=1);self.task.save()
        self.assertEqual(process_due(self.now),(0,0,0))
    def test_completed(self):
        self.client.post(f'/atividade/{self.task.pk}/concluir/')
        self.assertEqual(process_due(self.now),(0,0,0))
    def test_disabled_email(self):
        self.task.email_enabled=False;self.task.save()
        self.assertEqual(process_due(self.now),(1,0,0))
    def test_failure_retry(self):
        with patch('lembretes.services.send_mail',side_effect=OSError('SMTP')):
            self.assertEqual(process_due(self.now),(1,0,1))
        self.assertEqual(Notification.objects.count(),1)
        self.assertEqual(process_due(self.now),(0,0,0))
        self.assertEqual(process_due(self.now+timedelta(minutes=3)),(0,1,0))
    def test_zero_send(self):
        with patch('lembretes.services.send_mail',return_value=0):
            self.assertEqual(process_due(self.now),(1,0,1))
        self.task.refresh_from_db();self.assertIsNone(self.task.email_sent_at)
    def test_read_isolation(self):
        process_due(self.now);n=Notification.objects.get(task=self.task)
        self.client.post(f'/notificacao/{n.pk}/ler/');n.refresh_from_db();self.assertTrue(n.read)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(f'/notificacao/{n.pk}/ler/').status_code,404)
    def test_edit_resets(self):
        process_due(self.now)
        self.assertEqual(self.client.post(f'/atividade/{self.task.pk}/editar/',dict(title='Reagendada',due_at=timezone.localtime(self.now+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),email_enabled='on')).status_code,302)
        self.task.refresh_from_db();self.assertIsNone(self.task.email_sent_at)
        self.assertFalse(Notification.objects.filter(task=self.task).exists())
    def test_delete_cascade(self):
        process_due(self.now);self.client.post(f'/atividade/{self.task.pk}/excluir/')
        self.assertEqual(Notification.objects.count(),0)
    def test_html_escape(self):
        self.task.title='<script>alert(1)</script>';self.task.save()
        self.assertNotContains(self.client.get('/'),'<script>alert(1)</script>')
        self.assertContains(self.client.get('/'),'&lt;script&gt;')
    def test_command_once(self):
        from io import StringIO
        from django.core.management import call_command
        output=StringIO()
        call_command('process_reminders',stdout=output)
        self.assertIn('notificações=1 emails=1 falhas=0',output.getvalue())
    def test_command_loop(self):
        from django.core.management import call_command
        from io import StringIO
        with patch('lembretes.management.commands.process_reminders.time.sleep',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                call_command('process_reminders',loop=True,stdout=StringIO())
        self.assertEqual(Notification.objects.count(),1)
    def test_forms_render(self):
        self.assertContains(self.client.get('/atividade/nova/'),'Nova atividade')
        self.assertContains(self.client.get(f'/atividade/{self.task.pk}/editar/'),'Editar atividade')
