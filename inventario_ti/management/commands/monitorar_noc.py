from django.core.management import call_command
from django.core.management.base import BaseCommand

from inventario_ti.services_ad import monitorar_active_directory
from inventario_ti.services_servidor import monitorar_servidor_local
from inventario_ti.services_rede import monitorar_rede


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
        rede = monitorar_rede()
        self.stdout.write(
            self.style.SUCCESS(
                f"Rede | gateway={rede.gateway_ok} DNS={rede.dns_ok} switch={rede.switch_ok}"
            )
        )
        servidor = monitorar_servidor_local()
        self.stdout.write(
            self.style.SUCCESS(
                f"Servidor {servidor.hostname} | CPU={servidor.cpu_percentual}% "
                f"RAM={servidor.memoria_percentual}% DISCO={servidor.disco_percentual}%"
            )
        )
