import asyncio
import html
import re
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import NotificacaoUsuario
from core.services.permissions import PERFIS_TI
from .models import ImpressoraMonitorada


STATUS_RE = re.compile(r'<div id="moni_data">.*?<span[^>]*>(.*?)</span>', re.I | re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TONER_HEIGHT_RE = re.compile(r'class="tonerremain"[^>]*height="(\d+)"', re.I)


def _texto_html(valor):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", valor))).strip()


def consultar_impressora(impressora, timeout=4):
    request = Request(f"http://{impressora.ip}/general/status.html", headers={"User-Agent": "GSF-NOC/1.1"})
    with urlopen(request, timeout=timeout) as resposta:
        conteudo = resposta.read(256_000).decode("latin-1", errors="replace")
    titulo = TITLE_RE.search(conteudo)
    status = STATUS_RE.search(conteudo)
    toner_height = TONER_HEIGHT_RE.search(conteudo)
    toner_percentual = None
    if toner_height:
        toner_percentual = min(100, round(int(toner_height.group(1)) / 60 * 100))
    return {
        "modelo_detectado": _texto_html(titulo.group(1)).removeprefix("Brother ") if titulo else "",
        "status_dispositivo": _texto_html(status.group(1)) if status else "Pronta",
        "toner_percentual": toner_percentual,
    }


async def _consultar_snmp_async(ip, timeout=2):
    from pysnmp.hlapi.v3arch.asyncio import (
        CommunityData, ContextData, ObjectIdentity, ObjectType,
        SnmpEngine, UdpTransportTarget, get_cmd,
    )
    engine = SnmpEngine()
    try:
        target = await UdpTransportTarget.create((str(ip), 161), timeout=timeout, retries=0)
        erro, status, _, valores = await get_cmd(
            engine, CommunityData("public", mpModel=1), target, ContextData(),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
        )
        if erro or status or not valores:
            return ""
        return valores[0][1].prettyPrint().strip()
    finally:
        engine.close_dispatcher()


def consultar_snmp(ip, timeout=2):
    try:
        return asyncio.run(_consultar_snmp_async(ip, timeout))
    except Exception:
        return ""


def _usuarios_ti(impressora):
    usuarios = get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=PERFIS_TI)
    ).distinct()
    if impressora.unidade_id:
        usuarios = usuarios.filter(unidade=impressora.unidade)
    return usuarios


def _sincronizar_alerta(impressora):
    origem = "impressora_monitorada"
    objeto_id = str(impressora.pk)
    if not impressora.possui_alerta:
        NotificacaoUsuario.objects.filter(origem=origem, objeto_id=objeto_id, lida=False).update(
            lida=True, lida_em=timezone.now()
        )
        return
    estado = impressora.status_dispositivo or "Sem comunicação"
    if impressora.toner_percentual is not None and impressora.toner_percentual <= 20:
        estado = f"{estado} · Toner em {impressora.toner_percentual}%"
    for usuario in _usuarios_ti(impressora):
        notificacao, _ = NotificacaoUsuario.objects.get_or_create(
            usuario=usuario, origem=origem, objeto_id=objeto_id,
            defaults={"titulo": f"Impressora: {impressora.local}", "descricao": estado,
                      "tipo": "warning", "icone": "🖨️", "link": "/portal/noc/"},
        )
        if notificacao.descricao != estado:
            notificacao.descricao = estado
            notificacao.lida = False
            notificacao.lida_em = None
            notificacao.save(update_fields=["descricao", "lida", "lida_em"])


def atualizar_impressora(impressora):
    try:
        dados = consultar_impressora(impressora)
        impressora.online = True
        impressora.modelo_detectado = dados["modelo_detectado"] or impressora.modelo_detectado
        impressora.status_dispositivo = dados["status_dispositivo"]
        impressora.toner_percentual = dados["toner_percentual"]
        impressora.ultimo_erro = ""
    except Exception as exc:
        descricao_snmp = consultar_snmp(impressora.ip)
        if descricao_snmp.lower().startswith("brother"):
            impressora.online = True
            impressora.status_dispositivo = "Online via SNMP"
            impressora.ultimo_erro = f"Painel web indisponível: {exc}"[:1000]
        elif descricao_snmp:
            impressora.online = False
            impressora.status_dispositivo = "IP não pertence a uma impressora Brother"
            impressora.ultimo_erro = descricao_snmp[:1000]
        else:
            impressora.online = False
            impressora.status_dispositivo = "Sem comunicação"
            impressora.ultimo_erro = str(exc)[:1000]
    impressora.ultima_consulta = timezone.now()
    impressora.save(update_fields=["online", "modelo_detectado", "status_dispositivo", "toner_percentual", "ultimo_erro", "ultima_consulta", "atualizado_em"])
    _sincronizar_alerta(impressora)
    return impressora


def atualizar_todas_impressoras():
    return [atualizar_impressora(item) for item in ImpressoraMonitorada.objects.filter(ativo=True).select_related("unidade")]
