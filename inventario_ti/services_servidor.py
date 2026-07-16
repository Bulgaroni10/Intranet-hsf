import os
import socket
import time

import psutil
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import NotificacaoUsuario
from core.services.permissions import PERFIS_TI
from usuarios.models import Unidade
from .models import MonitoramentoServidor


def _sincronizar_alerta(item):
    origem = "capacidade_servidor"
    unidade = Unidade.objects.filter(sigla__iexact="HSFOS", ativo=True).first()
    usuarios = get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=PERFIS_TI)
    ).distinct()
    if unidade:
        usuarios = usuarios.filter(Q(unidade=unidade) | Q(unidades_permitidas=unidade)).distinct()
    if not item.possui_alerta:
        NotificacaoUsuario.objects.filter(origem=origem, objeto_id=str(item.pk), lida=False).update(
            lida=True, lida_em=timezone.now()
        )
        return
    partes = []
    if item.cpu_percentual is not None and item.cpu_percentual >= 90:
        partes.append(f"CPU {item.cpu_percentual}%")
    if item.memoria_percentual is not None and item.memoria_percentual >= 90:
        partes.append(f"memória {item.memoria_percentual}%")
    if item.disco_percentual is not None and item.disco_percentual >= 85:
        partes.append(f"disco {item.disco_percentual}%")
    descricao = "Capacidade crítica: " + ", ".join(partes)
    for usuario in usuarios:
        notificacao, _ = NotificacaoUsuario.objects.get_or_create(
            usuario=usuario, origem=origem, objeto_id=str(item.pk),
            defaults={"titulo": f"Servidor {item.hostname}", "descricao": descricao, "unidade": unidade,
                      "tipo": "danger", "icone": "🖥️", "link": "/portal/noc/"},
        )
        campos_atualizados = []
        if notificacao.unidade_id != getattr(unidade, "id", None):
            notificacao.unidade = unidade
            campos_atualizados.append("unidade")
        if notificacao.descricao != descricao:
            notificacao.descricao = descricao
            notificacao.lida = False
            notificacao.lida_em = None
            campos_atualizados.extend(["descricao", "lida", "lida_em"])
        if campos_atualizados:
            campos_atualizados.append("atualizado_em")
            notificacao.save(update_fields=campos_atualizados)


def monitorar_servidor_local():
    hostname = socket.gethostname()
    item, _ = MonitoramentoServidor.objects.get_or_create(hostname=hostname)
    memoria = psutil.virtual_memory()
    disco = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
    try:
        item.ip = socket.gethostbyname(hostname)
    except OSError:
        item.ip = None
    item.cpu_percentual = round(psutil.cpu_percent(interval=0.2), 1)
    item.memoria_percentual = round(memoria.percent, 1)
    item.memoria_total_gb = round(memoria.total / 1024 ** 3, 1)
    item.disco_percentual = round(disco.percent, 1)
    item.disco_livre_gb = round(disco.free / 1024 ** 3, 1)
    item.uptime_segundos = max(0, int(time.time() - psutil.boot_time()))
    item.detalhe = ""
    item.ultima_consulta = timezone.now()
    item.save()
    _sincronizar_alerta(item)
    return item
