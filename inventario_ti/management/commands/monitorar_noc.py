from django.core.management import call_command
from django.core.management.base import BaseCommand

from inventario_ti.services_ad import monitorar_active_directory


class Command(BaseCommand):
    help = "Atualiza todas as fontes operacionais do NOC."

    def handle(self, *args, **options):
        call_command("monitorar_impressoras", stdout=self.stdout, stderr=self.stderr)
        ad = monitorar_active_directory()
        self.stdout.write(
            self.style.SUCCESS(
                f"AD {ad.controlador} | {'online' if ad.online else 'offline'} | "
                f"LDAP={ad.ldap_ok} KERBEROS={ad.kerberos_ok} DNS={ad.dns_ok} SMB={ad.smb_ok}"
            )
        )
