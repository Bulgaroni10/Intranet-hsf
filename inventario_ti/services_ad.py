import socket
import time

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import NotificacaoUsuario
from core.services.permissions import PERFIS_TI
from usuarios.models import Unidade
from .models import MonitoramentoActiveDirectory


SERVICOS = {"ldap_ok": 389, "kerberos_ok": 88, "dns_ok": 53, "smb_ok": 445}


def _porta_aberta(host, porta, timeout=1.5):
    inicio = time.perf_counter()
    with socket.create_connection((host, porta), timeout=timeout):
        return round((time.perf_counter() - inicio) * 1000)


def _sincronizar_alerta(item):
    origem = "active_directory"
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
    falhas = [nome.removesuffix("_ok").upper() for nome in SERVICOS if not getattr(item, nome)]
    descricao = "Serviços indisponíveis: " + ", ".join(falhas)
    for usuario in usuarios:
        notificacao, _ = NotificacaoUsuario.objects.get_or_create(
            usuario=usuario, origem=origem, objeto_id=str(item.pk),
            defaults={"titulo": "Alerta do Active Directory", "descricao": descricao, "unidade": unidade,
                      "tipo": "danger", "icone": "🛡️", "link": "/portal/noc/"},
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
            notificacao.save(update_fields=campos_atualizados)


def monitorar_active_directory(controlador="HSFOS-AD.osascohsf.hosp"):
    item, _ = MonitoramentoActiveDirectory.objects.get_or_create(controlador=controlador)
    erros = []
    latencias = []
    try:
        item.ip = socket.gethostbyname(controlador)
    except OSError as exc:
        item.ip = None
        erros.append(f"DNS: {exc}")
    for campo, porta in SERVICOS.items():
        try:
            latencias.append(_porta_aberta(controlador, porta))
            setattr(item, campo, True)
        except OSError as exc:
            setattr(item, campo, False)
            erros.append(f"porta {porta}: {exc}")
    item.online = any(getattr(item, campo) for campo in SERVICOS)
    item.latencia_ms = min(latencias) if latencias else None
    item.detalhe = " | ".join(erros)[:2000]
    item.ultima_consulta = timezone.now()
    item.save()
    _sincronizar_alerta(item)
    return item
