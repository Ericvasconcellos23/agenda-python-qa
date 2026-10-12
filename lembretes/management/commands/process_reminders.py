"""Comando executável pelo servidor ou agendador de tarefas."""
import time
from django.core.management.base import BaseCommand
from lembretes.services import process_due
class Command(BaseCommand):
    help = "Processa lembretes vencidos; --loop mantém um único worker ativo"
    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")
    def handle(self, *args, **options):
        while True:
            created, sent, failed = process_due()
            self.stdout.write(f"notificações={created} emails={sent} falhas={failed}")
            if not options["loop"]:
                break
            time.sleep(30)
