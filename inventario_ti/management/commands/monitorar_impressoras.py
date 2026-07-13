from django.core.management.base import BaseCommand

from inventario_ti.services_impressoras import atualizar_todas_impressoras


class Command(BaseCommand):
    help = "Consulta as impressoras ativas e atualiza alertas do Portal/NOC."

    def handle(self, *args, **options):
        itens = atualizar_todas_impressoras()
        for item in itens:
            self.stdout.write(f"{item.ip} | {'online' if item.online else 'offline'} | {item.status_dispositivo}")
        self.stdout.write(self.style.SUCCESS(f"{len(itens)} impressoras consultadas."))
