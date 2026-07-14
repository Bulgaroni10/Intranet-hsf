import asyncio
import socket
import subprocess

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import NotificacaoUsuario
from core.services.permissions import PERFIS_TI
from usuarios.models import Unidade
from .models import MonitoramentoRede


def _ping(ip):
    resultado = subprocess.run(
        ["ping", "-n", "1", "-w", "1200", str(ip)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3, check=False,
    )
    return resultado.returncode == 0


def _dns_ok(ip):
    try:
        with socket.create_connection((str(ip), 53), timeout=1.5):
            return True
    except OSError:
        return False


async def _switch_snmp(ip):
    from pysnmp.hlapi.v3arch.asyncio import (
        CommunityData, ContextData, ObjectIdentity, ObjectType,
        SnmpEngine, UdpTransportTarget, get_cmd,
    )
    engine = SnmpEngine()
    try:
        target = await UdpTransportTarget.create((str(ip), 161), timeout=2, retries=0)
        erro, status, _, valores = await get_cmd(
            engine, CommunityData("public", mpModel=1), target, ContextData(),
            *[ObjectType(ObjectIdentity(oid)) for oid in (
                "1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1.3.0", "1.3.6.1.2.1.2.1.0",
            )],
        )
        if erro or status or len(valores) < 3:
            return None
        return {
            "modelo": valores[0][1].prettyPrint().strip(),
            "uptime": int(valores[1][1]) // 100,
            "interfaces": int(valores[2][1]),
        }
    finally:
        engine.close_dispatcher()


def _sincronizar_alerta(item):
    origem = "monitoramento_rede"
    unidade = Unidade.objects.filter(sigla__iexact="HSFOS", ativo=True).first()
    usuarios = get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=PERFIS_TI)
    ).distinct()
    if unidade:
        usuarios = usuarios.filter(Q(unidade=unidade) | Q(unidades_permitidas=unidade)).distinct()
    if not item.possui_alerta:
        NotificacaoUsuario.objects.filter(origem=origem, objeto_id=str(item.pk), lida=False).update(lida=True, lida_em=timezone.now())
        return
    falhas = [nome for nome, ok in (("gateway", item.gateway_ok), ("DNS", item.dns_ok), ("switch", item.switch_ok)) if not ok]
    descricao = "Indisponível: " + ", ".join(falhas)
    for usuario in usuarios:
        notificacao, _ = NotificacaoUsuario.objects.get_or_create(
            usuario=usuario, origem=origem, objeto_id=str(item.pk),
            defaults={"titulo": "Alerta de rede", "descricao": descricao, "unidade": unidade, "tipo": "danger", "icone": "🌐", "link": "/portal/noc/"},
        )
        campos_atualizados = []
        if notificacao.unidade_id != getattr(unidade, "id", None):
            notificacao.unidade = unidade
            campos_atualizados.append("unidade")
        if notificacao.descricao != descricao:
            notificacao.descricao, notificacao.lida, notificacao.lida_em = descricao, False, None
            campos_atualizados.extend(["descricao", "lida", "lida_em"])
        if campos_atualizados:
            notificacao.save(update_fields=campos_atualizados)


def monitorar_rede():
    item, _ = MonitoramentoRede.objects.get_or_create(nome="Rede HSFOS")
    item.gateway_ok = _ping(item.gateway_ip)
    item.dns_ok = _dns_ok(item.dns_ip)
    try:
        switch = asyncio.run(_switch_snmp(item.switch_ip))
    except Exception as exc:
        switch = None
        item.detalhe = str(exc)[:2000]
    item.switch_ok = bool(switch)
    if switch:
        item.switch_modelo = switch["modelo"]
        item.switch_uptime_segundos = switch["uptime"]
        item.switch_interfaces = switch["interfaces"]
        item.detalhe = ""
    item.ultima_consulta = timezone.now()
    item.save()
    _sincronizar_alerta(item)
    return item
