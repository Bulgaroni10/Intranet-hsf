from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import csv
import json
import re
from urllib.parse import urlencode

from core.services.permissions import usuario_eh_ti

from .models import ComputadorInventario, ErroAgenteInventario
from .services import (
    CAMPOS_MONITORADOS,
    computador_estava_offline,
    registrar_alteracoes_inventario,
    registrar_cadastro_computador,
    registrar_erro_agente,
    registrar_retorno_online,
)


def usuario_pode_acessar_inventario_ti(user):
    return usuario_eh_ti(user)


def valor_informado(valor):
    return bool(valor and str(valor).strip() not in ["", "-"])


def patrimonio_informado(computador):
    return valor_informado(computador.patrimonio)


def extrair_percentual_disco(valor):
    if not valor:
        return None

    match = re.search(r"\d+", str(valor))

    if not match:
        return None

    return int(match.group())


def computador_tem_disco_critico(computador):
    percentual = extrair_percentual_disco(computador.disco_percentual)
    return percentual is not None and percentual >= 90


def computador_tem_dados_incompletos(computador):
    campos_obrigatorios = [
        computador.hostname,
        computador.usuario,
        computador.ip_local,
        computador.mac,
        computador.sistema,
        computador.fabricante,
        computador.modelo,
        computador.serial,
    ]

    return any(not valor_informado(valor) for valor in campos_obrigatorios)


def computador_sem_heartbeat_recente(computador):
    if not computador.ultimo_contato:
        return True

    return computador.ultimo_contato < timezone.now() - timezone.timedelta(hours=24)


def aplicar_filtros_memoria(computadores, status, patrimonio, saude):
    filtrados = []

    for computador in computadores:
        if status == "online" and not computador.online:
            continue

        if status == "offline" and computador.online:
            continue

        if patrimonio == "sem" and patrimonio_informado(computador):
            continue

        if patrimonio == "com" and not patrimonio_informado(computador):
            continue

        if saude == "disco_critico" and not computador_tem_disco_critico(computador):
            continue

        if saude == "dados_incompletos" and not computador_tem_dados_incompletos(computador):
            continue

        if saude == "sem_heartbeat" and not computador_sem_heartbeat_recente(computador):
            continue

        filtrados.append(computador)

    return filtrados


def ordenar_computadores(computadores, ordenacao):
    ordenacoes = {
        "hostname": lambda pc: (pc.hostname or "").lower(),
        "ultimo_contato": lambda pc: pc.ultimo_contato or timezone.datetime.min.replace(tzinfo=timezone.get_current_timezone()),
        "usuario": lambda pc: (pc.usuario or "").lower(),
        "modelo": lambda pc: (pc.modelo or "").lower(),
    }

    chave = ordenacoes.get(ordenacao, ordenacoes["hostname"])
    reverso = ordenacao == "ultimo_contato"

    return sorted(computadores, key=chave, reverse=reverso)


def montar_resumo_inventario(computadores):
    total = len(computadores)
    online = len([pc for pc in computadores if pc.online])
    offline = total - online
    sem_patrimonio = len([pc for pc in computadores if not patrimonio_informado(pc)])
    disco_critico = len([pc for pc in computadores if computador_tem_disco_critico(pc)])
    dados_incompletos = len([pc for pc in computadores if computador_tem_dados_incompletos(pc)])
    sem_heartbeat = len([pc for pc in computadores if computador_sem_heartbeat_recente(pc)])

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "sem_patrimonio": sem_patrimonio,
        "disco_critico": disco_critico,
        "dados_incompletos": dados_incompletos,
        "sem_heartbeat": sem_heartbeat,
    }


def formatar_data_hora_csv(data_hora):
    if not data_hora:
        return ""

    try:
        return timezone.localtime(data_hora).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return data_hora.strftime("%d/%m/%Y %H:%M:%S")


def montar_response_csv(nome_arquivo):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    response.write("\ufeff")
    return response


def obter_filtros_inventario(request):
    return {
        "busca": request.GET.get("busca", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "patrimonio": request.GET.get("patrimonio", "").strip(),
        "saude": request.GET.get("saude", "").strip(),
        "fabricante": request.GET.get("fabricante", "").strip(),
        "sistema": request.GET.get("sistema", "").strip(),
        "ordenacao": request.GET.get("ordenacao", "hostname").strip() or "hostname",
    }


def filtrar_computadores_inventario(filtros):
    computadores = ComputadorInventario.objects.all()

    if filtros["busca"]:
        computadores = computadores.filter(
            Q(hostname__icontains=filtros["busca"]) |
            Q(usuario__icontains=filtros["busca"]) |
            Q(ip_local__icontains=filtros["busca"]) |
            Q(mac__icontains=filtros["busca"]) |
            Q(serial__icontains=filtros["busca"]) |
            Q(modelo__icontains=filtros["busca"]) |
            Q(patrimonio__icontains=filtros["busca"])
        )

    if filtros["fabricante"]:
        computadores = computadores.filter(fabricante=filtros["fabricante"])

    if filtros["sistema"]:
        computadores = computadores.filter(sistema=filtros["sistema"])

    lista_base = list(computadores)
    lista = aplicar_filtros_memoria(
        lista_base,
        filtros["status"],
        filtros["patrimonio"],
        filtros["saude"],
    )
    lista = ordenar_computadores(lista, filtros["ordenacao"])

    return lista_base, lista


def obter_filtros_erros_agentes(request):
    return {
        "busca": request.GET.get("busca", "").strip(),
        "categoria": request.GET.get("categoria", "").strip(),
        "agent_version": request.GET.get("agent_version", "").strip(),
        "vinculo": request.GET.get("vinculo", "").strip(),
        "data_inicio": request.GET.get("data_inicio", "").strip(),
        "data_fim": request.GET.get("data_fim", "").strip(),
    }


def filtrar_erros_agentes(filtros):
    erros = ErroAgenteInventario.objects.select_related("computador").all()

    if filtros["busca"]:
        erros = erros.filter(
            Q(hostname__icontains=filtros["busca"]) |
            Q(agent_version__icontains=filtros["busca"]) |
            Q(categoria__icontains=filtros["busca"]) |
            Q(mensagem__icontains=filtros["busca"]) |
            Q(detalhe__icontains=filtros["busca"])
        )

    if filtros["categoria"]:
        erros = erros.filter(categoria=filtros["categoria"])

    if filtros["agent_version"]:
        erros = erros.filter(agent_version=filtros["agent_version"])

    if filtros["vinculo"] == "vinculado":
        erros = erros.filter(computador__isnull=False)
    elif filtros["vinculo"] == "sem_vinculo":
        erros = erros.filter(computador__isnull=True)

    if filtros["data_inicio"]:
        erros = erros.filter(criado_em__date__gte=filtros["data_inicio"])

    if filtros["data_fim"]:
        erros = erros.filter(criado_em__date__lte=filtros["data_fim"])

    return erros


def montar_defaults_heartbeat(dados, ip_origem):
    return {
        "usuario": dados.get("usuario") or "-",
        "ip_origem": ip_origem,
        "ip_local": dados.get("ip_local") or None,
        "mac": dados.get("mac") or "-",
        "sistema": dados.get("sistema") or "-",
        "cpu": dados.get("cpu") or "-",
        "ram": dados.get("ram") or "-",
        "disco_total": dados.get("disco_total") or "-",
        "disco_livre": dados.get("disco_livre") or "-",
        "disco_percentual": dados.get("disco_percentual") or "-",
        "fabricante": dados.get("fabricante") or "-",
        "modelo": dados.get("modelo") or "-",
        "serial": dados.get("serial") or "-",
        "agent_version": dados.get("agent_version") or "-",
        "ultimo_contato": timezone.now(),
    }


def capturar_valores_monitorados(computador):
    return {
        campo: getattr(computador, campo, "")
        for campo in CAMPOS_MONITORADOS
    }


@csrf_exempt
def heartbeat(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método não permitido"}, status=405)

    try:
        dados = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido"}, status=400)

    hostname = dados.get("hostname", "").strip().upper()

    if not hostname:
        return JsonResponse({"ok": False, "erro": "Hostname obrigatório"}, status=400)

    ip_origem = request.META.get("REMOTE_ADDR")
    defaults = montar_defaults_heartbeat(dados, ip_origem)
    computador_anterior = ComputadorInventario.objects.filter(hostname=hostname).first()
    valores_anteriores = {}
    estava_offline = True
    ultimo_contato_anterior = None

    if computador_anterior:
        valores_anteriores = capturar_valores_monitorados(computador_anterior)
        estava_offline = computador_estava_offline(computador_anterior)
        ultimo_contato_anterior = computador_anterior.ultimo_contato

    computador, criado = ComputadorInventario.objects.update_or_create(
        hostname=hostname,
        defaults=defaults
    )

    eventos_registrados = 0

    if criado:
        registrar_cadastro_computador(computador)
        eventos_registrados += 1
    else:
        eventos = registrar_alteracoes_inventario(
            computador=computador,
            valores_anteriores=valores_anteriores,
            novos_valores=defaults,
        )
        eventos_registrados += len(eventos)

        if estava_offline:
            registrar_retorno_online(computador, ultimo_contato_anterior)
            eventos_registrados += 1

    return JsonResponse({
        "ok": True,
        "criado": criado,
        "hostname": computador.hostname,
        "status": computador.status_texto,
        "eventos_registrados": eventos_registrados,
    })


@csrf_exempt
def agent_error(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método não permitido"}, status=405)

    try:
        dados = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido"}, status=400)

    hostname = dados.get("hostname", "").strip().upper()
    mensagem = dados.get("mensagem", "").strip()

    if not hostname:
        return JsonResponse({"ok": False, "erro": "Hostname obrigatório"}, status=400)

    if not mensagem:
        return JsonResponse({"ok": False, "erro": "Mensagem obrigatória"}, status=400)

    erro = registrar_erro_agente(
        dados={
            **dados,
            "hostname": hostname,
        },
        ip_origem=request.META.get("REMOTE_ADDR"),
    )

    return JsonResponse({
        "ok": True,
        "erro_id": erro.id,
        "hostname": erro.hostname,
    })


@login_required
def dashboard(request):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    filtros = obter_filtros_inventario(request)

    fabricantes = ComputadorInventario.objects.exclude(
        fabricante__in=["", "-"]
    ).order_by(
        "fabricante"
    ).values_list(
        "fabricante",
        flat=True
    ).distinct()

    sistemas = ComputadorInventario.objects.exclude(
        sistema__in=["", "-"]
    ).order_by(
        "sistema"
    ).values_list(
        "sistema",
        flat=True
    ).distinct()

    lista_base, lista = filtrar_computadores_inventario(filtros)
    totais = montar_resumo_inventario(lista_base)

    query_string = urlencode({
        chave: valor for chave, valor in filtros.items() if valor
    })

    paginator = Paginator(lista, 20)
    pagina = request.GET.get("page")
    computadores_pagina = paginator.get_page(pagina)

    return render(request, "inventario_ti/dashboard.html", {
        "computadores": computadores_pagina,
        "filtros": filtros,
        "query_string": query_string,
        "fabricantes": fabricantes,
        "sistemas": sistemas,
        "totais": totais,
        "total_filtrado": len(lista),
    })


@login_required
def erros_agentes(request):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    filtros = obter_filtros_erros_agentes(request)
    erros = filtrar_erros_agentes(filtros)

    agora = timezone.now()
    ultimas_24h = agora - timezone.timedelta(hours=24)
    ultimos_7_dias = agora - timezone.timedelta(days=7)

    erros_base = ErroAgenteInventario.objects.all()
    totais = {
        "total": erros_base.count(),
        "ultimas_24h": erros_base.filter(criado_em__gte=ultimas_24h).count(),
        "ultimos_7_dias": erros_base.filter(criado_em__gte=ultimos_7_dias).count(),
        "hosts_afetados": erros_base.values("hostname").distinct().count(),
        "sem_vinculo": erros_base.filter(computador__isnull=True).count(),
        "filtrado": erros.count(),
    }

    categorias = ErroAgenteInventario.objects.exclude(
        categoria=""
    ).order_by(
        "categoria"
    ).values_list(
        "categoria",
        flat=True
    ).distinct()

    versoes = ErroAgenteInventario.objects.exclude(
        agent_version__in=["", "-"]
    ).order_by(
        "agent_version"
    ).values_list(
        "agent_version",
        flat=True
    ).distinct()

    categorias_resumo = erros_base.values(
        "categoria"
    ).annotate(
        total=Count("id")
    ).order_by(
        "-total",
        "categoria"
    )[:8]

    query_string = urlencode({
        chave: valor for chave, valor in filtros.items() if valor
    })

    paginator = Paginator(erros, 20)
    pagina = request.GET.get("page")
    erros_pagina = paginator.get_page(pagina)

    return render(request, "inventario_ti/erros_agentes.html", {
        "erros": erros_pagina,
        "filtros": filtros,
        "query_string": query_string,
        "categorias": categorias,
        "versoes": versoes,
        "categorias_resumo": categorias_resumo,
        "totais": totais,
    })


@login_required
def exportar_inventario_csv(request):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    filtros = obter_filtros_inventario(request)
    _, computadores = filtrar_computadores_inventario(filtros)
    response = montar_response_csv("inventario_ti.csv")
    writer = csv.writer(response, delimiter=";")

    writer.writerow([
        "Status",
        "Hostname",
        "Usuario",
        "IP origem",
        "IP local",
        "MAC",
        "Sistema",
        "CPU",
        "RAM",
        "Disco total",
        "Disco livre",
        "Uso disco",
        "Fabricante",
        "Modelo",
        "Serial",
        "Patrimonio",
        "Versao agente",
        "Ultimo contato",
        "Criado em",
        "Atualizado em",
    ])

    for computador in computadores:
        writer.writerow([
            computador.status_texto,
            computador.hostname,
            computador.usuario,
            computador.ip_origem or "",
            computador.ip_local or "",
            computador.mac,
            computador.sistema,
            computador.cpu,
            computador.ram,
            computador.disco_total,
            computador.disco_livre,
            computador.disco_percentual,
            computador.fabricante,
            computador.modelo,
            computador.serial,
            computador.patrimonio,
            computador.agent_version,
            formatar_data_hora_csv(computador.ultimo_contato),
            formatar_data_hora_csv(computador.criado_em),
            formatar_data_hora_csv(computador.atualizado_em),
        ])

    return response


@login_required
def exportar_erros_agentes_csv(request):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    filtros = obter_filtros_erros_agentes(request)
    erros = filtrar_erros_agentes(filtros)
    response = montar_response_csv("erros_agentes.csv")
    writer = csv.writer(response, delimiter=";")

    writer.writerow([
        "Data",
        "Hostname",
        "Computador vinculado",
        "Versao agente",
        "Categoria",
        "Mensagem",
        "Detalhe",
        "IP origem",
    ])

    for erro in erros:
        writer.writerow([
            formatar_data_hora_csv(erro.criado_em),
            erro.hostname,
            erro.computador.hostname if erro.computador else "",
            erro.agent_version,
            erro.categoria,
            erro.mensagem,
            erro.detalhe,
            erro.ip_origem or "",
        ])

    return response


@login_required
def detalhe(request, computador_id):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    computador = get_object_or_404(ComputadorInventario, id=computador_id)
    historicos = computador.historicos.all()[:30]
    disco_critico = computador_tem_disco_critico(computador)
    dados_incompletos = computador_tem_dados_incompletos(computador)
    sem_heartbeat = computador_sem_heartbeat_recente(computador)

    ficha_hardware = [
        ("Hostname", computador.hostname),
        ("Patrimônio", computador.patrimonio),
        ("Fabricante", computador.fabricante),
        ("Modelo", computador.modelo),
        ("Serial", computador.serial),
        ("Sistema operacional", computador.sistema),
        ("CPU", computador.cpu),
        ("RAM", computador.ram),
        ("Disco total", computador.disco_total),
        ("Disco livre", computador.disco_livre),
        ("Uso do disco", computador.disco_percentual),
    ]

    ficha_rede = [
        ("IP origem", computador.ip_origem or "-"),
        ("IP local", computador.ip_local or "-"),
        ("MAC", computador.mac),
        ("Usuário logado", computador.usuario),
        ("Versão do agente", computador.agent_version),
        ("Último contato", computador.ultimo_contato),
        ("Cadastrado em", computador.criado_em),
        ("Atualizado em", computador.atualizado_em),
    ]

    return render(request, "inventario_ti/detalhe.html", {
        "computador": computador,
        "disco_critico": disco_critico,
        "dados_incompletos": dados_incompletos,
        "sem_heartbeat": sem_heartbeat,
        "ficha_hardware": ficha_hardware,
        "ficha_rede": ficha_rede,
        "historicos": historicos,
    })
