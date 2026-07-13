from django.core.management.base import BaseCommand, CommandError

from inventario_ti.models import ImpressoraMonitorada
from usuarios.models import Unidade


IMPRESSORAS = [
    ("192.168.0.204", "MFC-L6902DW", "RECEPÇÃO"),
    ("192.168.0.145", "HL-L6202DW", "ENDOSCOPIA"),
    ("192.168.0.14", "MFC-L6902DW", "FARMÁCIA"),
    ("192.168.0.201", "HL-L6202DW", "CONSULTÓRIO 1"),
    ("192.168.0.207", "DCP-L5500D", "CENTRO CIRÚRGICO"),
    ("192.168.0.223", "DCP-L5652DN", "FATURAMENTO"),
    ("192.168.0.53", "HL-L6202DW", "CONSULTÓRIO 2"),
    ("192.168.0.57", "HL-L6202DW", "NUTRIÇÃO"),
    ("192.168.0.58", "HL-L6202DW", "CONSULTÓRIO 3"),
    ("192.168.0.59", "MFC-L6902DW", "UTI ADULTO"),
    ("192.168.0.61", "HL-L6202DW", "OFTALMOLOGIA"),
    ("192.168.0.142", "MFC-L5902DW", "RH"),
    ("192.168.0.155", "HL-L6202DW", "TI"),
]


class Command(BaseCommand):
    help = "Cadastra ou atualiza a frota inicial de impressoras do HSFOS."

    def handle(self, *args, **options):
        unidade = Unidade.objects.filter(sigla__iexact="HSFOS").first()
        if not unidade:
            raise CommandError("Unidade HSFOS não encontrada.")
        for ip, modelo, local in IMPRESSORAS:
            _, criada = ImpressoraMonitorada.objects.update_or_create(
                ip=ip, defaults={"unidade": unidade, "modelo_informado": modelo, "local": local, "ativo": True}
            )
            self.stdout.write(f"{'Criada' if criada else 'Atualizada'}: {ip} - {local}")
