import asyncio
import html
import re
import ssl
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import NotificacaoUsuario
from core.services.permissions import PERFIS_TI
from .models import ImpressoraMonitorada


STATUS_RE = re.compile(r'<div id="moni_data">.*?<span[^>]*>(.*?)</span>', re.I | re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TONER_HEIGHT_RE = re.compile(r'class="tonerremain"[^>]*height="(\d+)"', re.I)
SUPPLY_DESCRIPTION_OID = "1.3.6.1.2.1.43.11.1.1.6.1"
SUPPLY_MAX_OID = "1.3.6.1.2.1.43.11.1.1.8.1"
SUPPLY_LEVEL_OID = "1.3.6.1.2.1.43.11.1.1.9.1"
FABRICANTES_SUPORTADOS = ("brother", "kyocera", "ricoh")


def _contexto_ssl_impressora():
    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    return contexto


def _abrir_url_impressora(request, timeout):
    # Não herdar HTTP_PROXY/HTTPS_PROXY do Windows ou da conta do serviço.
    # As impressoras são acessadas diretamente pelos IPs da rede interna.
    opener = build_opener(
        ProxyHandler({}),
        HTTPSHandler(context=_contexto_ssl_impressora()),
    )
    return opener.open(request, timeout=timeout)


def _texto_html(valor):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", valor))).strip()


def consultar_impressora(impressora, timeout=4):
    ultimo_erro = None
    conteudo = None
    # Algumas Brother aceitam somente HTTP, outras somente HTTPS e modelos
    # antigos usam certificado autoassinado. Tentamos ambos sem depender do
    # redirecionamento da porta 80.
    for protocolo in ("http", "https"):
        request = Request(
            f"{protocolo}://{impressora.ip}/general/status.html",
            headers={"User-Agent": "GSF-NOC/1.1"},
        )
        try:
            with _abrir_url_impressora(request, timeout) as resposta:
                conteudo = resposta.read(256_000).decode("latin-1", errors="replace")
            break
        except Exception as exc:
            ultimo_erro = exc
    if conteudo is None:
        raise ultimo_erro
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


async def _caminhar_oid(engine, auth, target, context, oid):
    from pysnmp.hlapi.v3arch.asyncio import ObjectIdentity, ObjectType, walk_cmd

    resultado = {}
    async for erro, status, _, valores in walk_cmd(
        engine, auth, target, context, ObjectType(ObjectIdentity(oid)),
        lexicographicMode=False,
    ):
        if erro or status:
            break
        for nome, valor in valores:
            oid_atual = nome.prettyPrint()
            if oid_atual.startswith(f"{oid}."):
                resultado[oid_atual[len(oid) + 1:]] = valor.prettyPrint().strip()
    return resultado


async def _consultar_suprimentos_snmp_async(ip, timeout=2):
    from pysnmp.hlapi.v3arch.asyncio import (
        CommunityData, ContextData, SnmpEngine, UdpTransportTarget,
    )

    engine = SnmpEngine()
    try:
        target = await UdpTransportTarget.create((str(ip), 161), timeout=timeout, retries=0)
        auth = CommunityData("public", mpModel=1)
        context = ContextData()
        descricoes, capacidades, niveis = await asyncio.gather(
            _caminhar_oid(engine, auth, target, context, SUPPLY_DESCRIPTION_OID),
            _caminhar_oid(engine, auth, target, context, SUPPLY_MAX_OID),
            _caminhar_oid(engine, auth, target, context, SUPPLY_LEVEL_OID),
        )
        percentuais = {"toner_percentual": [], "cilindro_percentual": []}
        for indice, descricao in descricoes.items():
            try:
                capacidade = int(capacidades.get(indice, ""))
                nivel = int(niveis.get(indice, ""))
            except (TypeError, ValueError):
                continue
            if capacidade <= 0 or nivel < 0:
                continue
            percentual = max(0, min(100, round(nivel / capacidade * 100)))
            descricao = descricao.casefold()
            if "toner" in descricao:
                percentuais["toner_percentual"].append(percentual)
            elif any(termo in descricao for termo in ("drum", "tambor", "cilindro")):
                percentuais["cilindro_percentual"].append(percentual)
        return {
            chave: min(valores) if valores else None
            for chave, valores in percentuais.items()
        }
    finally:
        engine.close_dispatcher()


def consultar_suprimentos_snmp(ip, timeout=2):
    try:
        return asyncio.run(_consultar_suprimentos_snmp_async(ip, timeout))
    except Exception:
        return {"toner_percentual": None, "cilindro_percentual": None}


def _fabricante_snmp(descricao):
    texto = (descricao or "").casefold()
    return next((fabricante for fabricante in FABRICANTES_SUPORTADOS if fabricante in texto), "")


def _modelo_snmp(descricao):
    descricao = re.sub(r"\s+", " ", (descricao or "")).strip()
    if not descricao:
        return ""
    # O sysDescr varia por fabricante. Mantê-lo é mais confiável que o driver
    # instalado no servidor de impressão e ainda permite identificar o modelo.
    return descricao[:180]


def _usuarios_ti(impressora):
    usuarios = get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=PERFIS_TI)
    ).distinct()
    if impressora.unidade_id:
        usuarios = usuarios.filter(Q(unidade=impressora.unidade) | Q(unidades_permitidas=impressora.unidade)).distinct()
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
    if impressora.cilindro_percentual is not None and impressora.cilindro_percentual <= 20:
        estado = f"{estado} · Cilindro em {impressora.cilindro_percentual}%"
    for usuario in _usuarios_ti(impressora):
        notificacao, _ = NotificacaoUsuario.objects.get_or_create(
            usuario=usuario, origem=origem, objeto_id=objeto_id,
            defaults={"titulo": f"Impressora: {impressora.local}", "descricao": estado, "unidade": impressora.unidade,
                      "tipo": "warning", "icone": "🖨️", "link": "/portal/noc/"},
        )
        campos_atualizados = []
        if notificacao.unidade_id != impressora.unidade_id:
            notificacao.unidade = impressora.unidade
            campos_atualizados.append("unidade")
        if notificacao.descricao != estado:
            notificacao.descricao = estado
            notificacao.lida = False
            notificacao.lida_em = None
            campos_atualizados.extend(["descricao", "lida", "lida_em"])
        if campos_atualizados:
            notificacao.save(update_fields=campos_atualizados)


def atualizar_impressora(impressora):
    try:
        dados = consultar_impressora(impressora)
        suprimentos_snmp = consultar_suprimentos_snmp(impressora.ip)
        impressora.online = True
        impressora.modelo_detectado = dados["modelo_detectado"] or impressora.modelo_detectado
        impressora.status_dispositivo = dados["status_dispositivo"]
        impressora.toner_percentual = (
            dados["toner_percentual"]
            if dados["toner_percentual"] is not None
            else suprimentos_snmp["toner_percentual"]
        )
        impressora.cilindro_percentual = suprimentos_snmp["cilindro_percentual"]
        impressora.ultimo_erro = ""
    except Exception as exc:
        descricao_snmp = consultar_snmp(impressora.ip)
        fabricante = _fabricante_snmp(descricao_snmp)
        if fabricante:
            suprimentos_snmp = consultar_suprimentos_snmp(impressora.ip)
            impressora.online = True
            impressora.status_dispositivo = "Online via SNMP"
            impressora.modelo_detectado = _modelo_snmp(descricao_snmp) or impressora.modelo_detectado
            if suprimentos_snmp["toner_percentual"] is not None:
                impressora.toner_percentual = suprimentos_snmp["toner_percentual"]
            if suprimentos_snmp["cilindro_percentual"] is not None:
                impressora.cilindro_percentual = suprimentos_snmp["cilindro_percentual"]
            impressora.ultimo_erro = f"Painel web indisponível: {exc}"[:1000]
        elif descricao_snmp:
            impressora.online = False
            impressora.status_dispositivo = "IP não identificado como impressora suportada"
            impressora.ultimo_erro = descricao_snmp[:1000]
        else:
            impressora.online = False
            impressora.status_dispositivo = "Sem comunicação"
            impressora.ultimo_erro = str(exc)[:1000]
    impressora.ultima_consulta = timezone.now()
    impressora.save(update_fields=["online", "modelo_detectado", "status_dispositivo", "toner_percentual", "cilindro_percentual", "ultimo_erro", "ultima_consulta", "atualizado_em"])
    _sincronizar_alerta(impressora)
    return impressora


def atualizar_todas_impressoras():
    return [atualizar_impressora(item) for item in ImpressoraMonitorada.objects.filter(ativo=True).select_related("unidade")]
