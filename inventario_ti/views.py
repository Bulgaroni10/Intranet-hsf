from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import csv
from io import BytesIO
import json
import re
import uuid
from urllib.parse import urlencode
from django.urls import reverse

import qrcode
from qrcode.image.svg import SvgPathImage

from core.services.permissions import usuario_eh_ti
from usuarios.models import Setor, Unidade

from .models import ComputadorInventario, ErroAgenteInventario, MovimentacaoPatrimonioTI, MovimentacaoSuprimentoTI, PatrimonioTI, SuprimentoTI
from .services import (
    CAMPOS_MONITORADOS,
    computador_estava_offline,
    registrar_alteracoes_inventario,
    registrar_cadastro_computador,
    registrar_erro_agente,
    registrar_retorno_online,
    reconciliar_patrimonios_por_serial,
    vincular_patrimonio_por_serial,
)
from .services_suprimentos import LIMITE_ALERTA_SUPRIMENTO, sincronizar_alerta_suprimento

VERSAO_AGENT_ATUAL = "2.1.0"


def usuario_pode_acessar_inventario_ti(user):
    return usuario_eh_ti(user)


def usuario_pode_gerenciar_patrimonio_ti(user):
    return usuario_eh_ti(user)


def obter_unidade_usuario(user):
    return getattr(user, "unidade", None)


def aplicar_escopo_unidade(queryset, user, campo="unidade"):
    unidade = obter_unidade_usuario(user)

    if unidade:
        return queryset.filter(**{campo: unidade})

    return queryset


def resolver_unidade_payload(dados):
    sigla = (
        dados.get("unit_code") or
        dados.get("unidade_sigla") or
        dados.get("unidade") or
        ""
    )
    sigla = str(sigla).strip().upper()

    if not sigla:
        return None

    return Unidade.objects.filter(sigla__iexact=sigla, ativo=True).first()


def valor_informado(valor):
    return bool(valor and str(valor).strip() not in ["", "-"])


def patrimonio_informado(computador):
    return valor_informado(computador.patrimonio)


def diagnosticar_pendencias_patrimonio(computadores):
    pendentes = [pc for pc in computadores if not patrimonio_informado(pc)]
    chaves = {
        (pc.unidade_id, str(pc.serial).strip().casefold())
        for pc in pendentes
        if valor_informado(pc.serial)
    }
    patrimonios_por_serial = {}

    if chaves:
        unidades = {unidade_id for unidade_id, _serial in chaves if unidade_id}
        patrimonios = PatrimonioTI.objects.filter(
            unidade_id__in=unidades,
            ativo=True,
        ).select_related("computador")
        for item in patrimonios:
            chave = (item.unidade_id, (item.serial or "").strip().casefold())
            if chave in chaves:
                patrimonios_por_serial.setdefault(chave, []).append(item)

    for computador in computadores:
        computador.pendencia_patrimonio = ""
        computador.pendencia_patrimonio_codigo = ""
        if patrimonio_informado(computador):
            continue

        if not valor_informado(computador.serial):
            computador.pendencia_patrimonio = "Serial não informado pelo equipamento"
            continue

        chave = (computador.unidade_id, str(computador.serial).strip().casefold())
        candidatos = patrimonios_por_serial.get(chave, [])
        if not candidatos:
            computador.pendencia_patrimonio = "Serial ainda não cadastrado no patrimônio"
        elif len(candidatos) > 1:
            computador.pendencia_patrimonio = "Serial duplicado no cadastro patrimonial"
        elif candidatos[0].tipo not in ("computador", "notebook"):
            computador.pendencia_patrimonio = "Ativo cadastrado com tipo incompatível"
            computador.pendencia_patrimonio_codigo = candidatos[0].codigo
        elif candidatos[0].computador_id and candidatos[0].computador_id != computador.id:
            computador.pendencia_patrimonio = "Patrimônio já vinculado a outro computador"
            computador.pendencia_patrimonio_codigo = candidatos[0].codigo
        else:
            computador.pendencia_patrimonio = "Aguardando o próximo heartbeat para vincular"
            computador.pendencia_patrimonio_codigo = candidatos[0].codigo

    return computadores


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


def computador_com_agente_desatualizado(computador):
    return (computador.agent_version or "-").strip() != VERSAO_AGENT_ATUAL


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

        if saude == "agente_desatualizado" and not computador_com_agente_desatualizado(computador):
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
    agentes_desatualizados = len([pc for pc in computadores if computador_com_agente_desatualizado(pc)])

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "sem_patrimonio": sem_patrimonio,
        "disco_critico": disco_critico,
        "dados_incompletos": dados_incompletos,
        "sem_heartbeat": sem_heartbeat,
        "agentes_desatualizados": agentes_desatualizados,
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


COLUNAS_IMPORTACAO_PATRIMONIO = [
    "codigo", "tipo", "status", "unidade", "setor", "responsavel",
    "fabricante", "modelo", "serial", "observacao",
]


def ler_csv_patrimonios(arquivo):
    conteudo = arquivo.read()
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("cp1252")

    linhas = texto.splitlines()
    if not linhas:
        raise ValueError("O arquivo CSV está vazio.")

    try:
        delimitador = csv.Sniffer().sniff(texto[:4096], delimiters=";,\t").delimiter
    except csv.Error:
        delimitador = ";"

    leitor = csv.DictReader(linhas, delimiter=delimitador)
    cabecalhos = {(item or "").strip().lower() for item in (leitor.fieldnames or [])}
    if "codigo" not in cabecalhos:
        raise ValueError("A coluna obrigatória 'codigo' não foi encontrada.")

    return [
        {(chave or "").strip().lower(): (valor or "").strip() for chave, valor in linha.items()}
        for linha in leitor
        if any((valor or "").strip() for valor in linha.values())
    ]


def validar_linhas_importacao_patrimonio(linhas, user):
    erros = []
    preparados = []
    codigos_arquivo = set()
    tipos_validos = {valor for valor, _rotulo in PatrimonioTI.TIPO_CHOICES}
    status_validos = {valor for valor, _rotulo in PatrimonioTI.STATUS_CHOICES}
    unidade_usuario = obter_unidade_usuario(user)

    for numero, linha in enumerate(linhas, start=2):
        codigo = linha.get("codigo", "").strip()
        tipo = linha.get("tipo", "computador").strip().lower() or "computador"
        status = linha.get("status", "em_uso").strip().lower() or "em_uso"
        sigla = linha.get("unidade", "").strip()
        nome_setor = linha.get("setor", "").strip()

        if not codigo:
            erros.append(f"Linha {numero}: código obrigatório.")
            continue
        chave_codigo = codigo.casefold()
        if chave_codigo in codigos_arquivo:
            erros.append(f"Linha {numero}: código {codigo} duplicado no arquivo.")
            continue
        codigos_arquivo.add(chave_codigo)

        if PatrimonioTI.objects.filter(codigo__iexact=codigo).exists():
            erros.append(f"Linha {numero}: o patrimônio {codigo} já está cadastrado.")
        if tipo not in tipos_validos:
            erros.append(f"Linha {numero}: tipo '{tipo}' inválido.")
        if status not in status_validos:
            erros.append(f"Linha {numero}: status '{status}' inválido.")

        unidade = unidade_usuario
        if user.is_superuser:
            unidade = Unidade.objects.filter(sigla__iexact=sigla, ativo=True).first()
        elif sigla and unidade_usuario and sigla.casefold() != unidade_usuario.sigla.casefold():
            unidade = None
        if not unidade:
            erros.append(f"Linha {numero}: unidade '{sigla}' inválida ou não permitida.")

        setor = None
        if nome_setor:
            setor = Setor.objects.filter(nome__iexact=nome_setor, ativo=True).first()
            if not setor:
                erros.append(f"Linha {numero}: setor '{nome_setor}' não cadastrado.")

        preparados.append({
            "codigo": codigo, "tipo": tipo, "status": status,
            "unidade": unidade, "setor": setor,
            "responsavel": linha.get("responsavel", ""),
            "fabricante": linha.get("fabricante", ""),
            "modelo": linha.get("modelo", ""),
            "serial": linha.get("serial", ""),
            "observacao": linha.get("observacao", ""),
        })

    return preparados, erros


def obter_filtros_inventario(request):
    return {
        "busca": request.GET.get("busca", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "patrimonio": request.GET.get("patrimonio", "").strip(),
        "saude": request.GET.get("saude", "").strip(),
        "fabricante": request.GET.get("fabricante", "").strip(),
        "sistema": request.GET.get("sistema", "").strip(),
        "unidade": request.GET.get("unidade", "").strip(),
        "ordenacao": request.GET.get("ordenacao", "hostname").strip() or "hostname",
    }


def filtrar_computadores_inventario(filtros, user=None):
    computadores = ComputadorInventario.objects.select_related("unidade", "patrimonio_vinculado")

    if user:
        computadores = aplicar_escopo_unidade(computadores, user)

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

    if filtros["unidade"]:
        computadores = computadores.filter(unidade_id=filtros["unidade"])

    lista_base = list(computadores)
    diagnosticar_pendencias_patrimonio(lista_base)
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


def filtrar_erros_agentes(filtros, user=None):
    erros = ErroAgenteInventario.objects.select_related("computador").all()

    if user:
        erros = aplicar_escopo_unidade(erros, user)

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


def obter_filtros_patrimonio(request):
    return {
        "busca": request.GET.get("busca", "").strip(),
        "tipo": request.GET.get("tipo", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "unidade": request.GET.get("unidade", "").strip(),
        "setor": request.GET.get("setor", "").strip(),
        "vinculo": request.GET.get("vinculo", "").strip(),
    }


def filtrar_patrimonios(filtros, user=None):
    patrimonios = PatrimonioTI.objects.select_related(
        "computador",
        "unidade",
        "setor",
    )

    if user:
        patrimonios = aplicar_escopo_unidade(patrimonios, user)

    if filtros["busca"]:
        patrimonios = patrimonios.filter(
            Q(codigo__icontains=filtros["busca"]) |
            Q(responsavel__icontains=filtros["busca"]) |
            Q(fabricante__icontains=filtros["busca"]) |
            Q(modelo__icontains=filtros["busca"]) |
            Q(serial__icontains=filtros["busca"]) |
            Q(nota_fiscal__icontains=filtros["busca"]) |
            Q(computador__hostname__icontains=filtros["busca"])
        )

    if filtros["tipo"]:
        patrimonios = patrimonios.filter(tipo=filtros["tipo"])

    if filtros["status"]:
        patrimonios = patrimonios.filter(status=filtros["status"])

    if filtros["unidade"]:
        patrimonios = patrimonios.filter(unidade_id=filtros["unidade"])

    if filtros["setor"]:
        patrimonios = patrimonios.filter(setor_id=filtros["setor"])

    if filtros["vinculo"] == "vinculado":
        patrimonios = patrimonios.filter(computador__isnull=False)
    elif filtros["vinculo"] == "sem_vinculo":
        patrimonios = patrimonios.filter(computador__isnull=True)

    return patrimonios


def montar_form_data_patrimonio(request):
    return {
        "codigo": request.POST.get("codigo", "").strip().upper(),
        "tipo": request.POST.get("tipo", "computador").strip(),
        "status": request.POST.get("status", "em_uso").strip(),
        "computador": request.POST.get("computador", "").strip(),
        "unidade": request.POST.get("unidade", "").strip(),
        "setor": request.POST.get("setor", "").strip(),
        "responsavel": request.POST.get("responsavel", "").strip(),
        "fabricante": request.POST.get("fabricante", "").strip(),
        "modelo": request.POST.get("modelo", "").strip(),
        "serial": request.POST.get("serial", "").strip(),
        "nota_fiscal": request.POST.get("nota_fiscal", "").strip(),
        "data_aquisicao": request.POST.get("data_aquisicao", "").strip(),
        "valor_aquisicao": request.POST.get("valor_aquisicao", "").strip().replace(",", "."),
        "observacao": request.POST.get("observacao", "").strip(),
        "ativo": request.POST.get("ativo", "on") == "on",
    }


def patrimonio_para_form_data(patrimonio):
    return {
        "codigo": patrimonio.codigo,
        "tipo": patrimonio.tipo,
        "status": patrimonio.status,
        "computador": str(patrimonio.computador_id) if patrimonio.computador_id else "",
        "unidade": str(patrimonio.unidade_id) if patrimonio.unidade_id else "",
        "setor": str(patrimonio.setor_id) if patrimonio.setor_id else "",
        "responsavel": patrimonio.responsavel,
        "fabricante": patrimonio.fabricante,
        "modelo": patrimonio.modelo,
        "serial": patrimonio.serial,
        "nota_fiscal": patrimonio.nota_fiscal,
        "data_aquisicao": patrimonio.data_aquisicao.isoformat() if patrimonio.data_aquisicao else "",
        "valor_aquisicao": patrimonio.valor_aquisicao if patrimonio.valor_aquisicao is not None else "",
        "observacao": patrimonio.observacao,
        "ativo": patrimonio.ativo,
    }


def contexto_formulario_patrimonio(form_data, patrimonio=None, user=None):
    computadores = ComputadorInventario.objects.order_by("hostname")
    unidade_usuario = obter_unidade_usuario(user)

    if unidade_usuario:
        computadores = computadores.filter(unidade=unidade_usuario)

    if patrimonio and patrimonio.computador_id:
        computadores = computadores.filter(
            Q(patrimonio_vinculado__isnull=True) |
            Q(id=patrimonio.computador_id)
        )
    else:
        computadores = computadores.filter(patrimonio_vinculado__isnull=True)

    return {
        "form_data": form_data,
        "patrimonio": patrimonio,
        "tipos": PatrimonioTI.TIPO_CHOICES,
        "status_choices": PatrimonioTI.STATUS_CHOICES,
        "computadores": computadores,
        "unidades": Unidade.objects.filter(id=unidade_usuario.id).order_by("nome") if unidade_usuario else Unidade.objects.filter(ativo=True).order_by("nome"),
        "setores": Setor.objects.filter(ativo=True).order_by("nome"),
    }


def aplicar_form_data_patrimonio(patrimonio, form_data):
    patrimonio.codigo = form_data["codigo"]
    patrimonio.tipo = form_data["tipo"]
    patrimonio.status = form_data["status"]
    patrimonio.computador_id = form_data["computador"] or None
    patrimonio.unidade_id = form_data["unidade"] or None
    patrimonio.setor_id = form_data["setor"] or None
    patrimonio.responsavel = form_data["responsavel"]
    patrimonio.fabricante = form_data["fabricante"]
    patrimonio.modelo = form_data["modelo"]
    patrimonio.serial = form_data["serial"]
    patrimonio.nota_fiscal = form_data["nota_fiscal"]
    patrimonio.data_aquisicao = form_data["data_aquisicao"] or None
    patrimonio.valor_aquisicao = form_data["valor_aquisicao"] or None
    patrimonio.observacao = form_data["observacao"]
    patrimonio.ativo = form_data["ativo"]


def aplicar_unidade_usuario_form_data(form_data, user):
    unidade_usuario = obter_unidade_usuario(user)

    if unidade_usuario:
        form_data["unidade"] = str(unidade_usuario.id)

    return form_data


def computador_pode_ser_vinculado(computador_id, user):
    if not computador_id:
        return True

    computadores = ComputadorInventario.objects.filter(id=computador_id)
    computadores = aplicar_escopo_unidade(computadores, user)

    return computadores.exists()


def sincronizar_patrimonio_computador(patrimonio, computador_anterior_id=None):
    if computador_anterior_id and computador_anterior_id != patrimonio.computador_id:
        ComputadorInventario.objects.filter(id=computador_anterior_id).update(patrimonio="-")

    if patrimonio.computador_id:
        ComputadorInventario.objects.filter(id=patrimonio.computador_id).update(patrimonio=patrimonio.codigo)


def registrar_movimentacao_patrimonio(patrimonio, tipo, usuario, observacao="", origem=None):
    MovimentacaoPatrimonioTI.objects.create(
        patrimonio=patrimonio,
        tipo=tipo,
        unidade_origem=origem.get("unidade") if origem else None,
        setor_origem=origem.get("setor") if origem else None,
        responsavel_origem=origem.get("responsavel") if origem else "",
        unidade_destino=patrimonio.unidade,
        setor_destino=patrimonio.setor,
        responsavel_destino=patrimonio.responsavel,
        observacao=observacao,
        usuario=usuario,
    )


def snapshot_origem_patrimonio(patrimonio):
    return {
        "unidade": patrimonio.unidade,
        "setor": patrimonio.setor,
        "responsavel": patrimonio.responsavel,
    }


def montar_defaults_heartbeat(dados, ip_origem, unidade=None):
    return {
        "unidade": unidade,
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
    unidade = resolver_unidade_payload(dados)

    if not unidade:
        return JsonResponse({"ok": False, "erro": "Unidade obrigatória ou inválida"}, status=400)

    defaults = montar_defaults_heartbeat(dados, ip_origem, unidade)
    computador_anterior = ComputadorInventario.objects.filter(
        hostname=hostname,
        unidade=unidade,
    ).first()
    valores_anteriores = {}
    estava_offline = True
    ultimo_contato_anterior = None

    if computador_anterior:
        valores_anteriores = capturar_valores_monitorados(computador_anterior)
        estava_offline = computador_estava_offline(computador_anterior)
        ultimo_contato_anterior = computador_anterior.ultimo_contato

    computador, criado = ComputadorInventario.objects.update_or_create(
        hostname=hostname,
        unidade=unidade,
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

    patrimonio_vinculado = vincular_patrimonio_por_serial(computador)
    if patrimonio_vinculado and not computador_anterior:
        eventos_registrados += 1

    return JsonResponse({
        "ok": True,
        "criado": criado,
        "hostname": computador.hostname,
        "status": computador.status_texto,
        "unidade": computador.unidade.sigla if computador.unidade else "",
        "eventos_registrados": eventos_registrados,
        "patrimonio": patrimonio_vinculado.codigo if patrimonio_vinculado else computador.patrimonio,
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

    unidade = resolver_unidade_payload(dados)

    if not unidade:
        return JsonResponse({"ok": False, "erro": "Unidade obrigatória ou inválida"}, status=400)

    erro = registrar_erro_agente(
        dados={
            **dados,
            "hostname": hostname,
        },
        ip_origem=request.META.get("REMOTE_ADDR"),
        unidade=resolver_unidade_payload(dados),
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

    fabricantes_qs = aplicar_escopo_unidade(ComputadorInventario.objects.all(), request.user)
    fabricantes = fabricantes_qs.exclude(
        fabricante__in=["", "-"]
    ).order_by(
        "fabricante"
    ).values_list(
        "fabricante",
        flat=True
    ).distinct()

    sistemas = fabricantes_qs.exclude(
        sistema__in=["", "-"]
    ).order_by(
        "sistema"
    ).values_list(
        "sistema",
        flat=True
    ).distinct()

    if request.user.is_superuser:
        unidades = Unidade.objects.filter(ativo=True).order_by("nome")
    else:
        unidades = Unidade.objects.filter(id=getattr(request.user, "unidade_id", None), ativo=True)

    lista_base, lista = filtrar_computadores_inventario(filtros, request.user)
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
        "unidades": unidades,
        "totais": totais,
        "total_filtrado": len(lista),
        "agora": timezone.localtime(),
        "versao_agent_atual": VERSAO_AGENT_ATUAL,
    })


@login_required
def erros_agentes(request):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    filtros = obter_filtros_erros_agentes(request)
    erros = filtrar_erros_agentes(filtros, request.user)

    agora = timezone.now()
    ultimas_24h = agora - timezone.timedelta(hours=24)
    ultimos_7_dias = agora - timezone.timedelta(days=7)

    erros_base = aplicar_escopo_unidade(ErroAgenteInventario.objects.all(), request.user)
    totais = {
        "total": erros_base.count(),
        "ultimas_24h": erros_base.filter(criado_em__gte=ultimas_24h).count(),
        "ultimos_7_dias": erros_base.filter(criado_em__gte=ultimos_7_dias).count(),
        "hosts_afetados": erros_base.values("hostname").distinct().count(),
        "sem_vinculo": erros_base.filter(computador__isnull=True).count(),
        "filtrado": erros.count(),
    }

    categorias = erros_base.exclude(
        categoria=""
    ).order_by(
        "categoria"
    ).values_list(
        "categoria",
        flat=True
    ).distinct()

    versoes = erros_base.exclude(
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
    _, computadores = filtrar_computadores_inventario(filtros, request.user)
    response = montar_response_csv("inventario_ti.csv")
    writer = csv.writer(response, delimiter=";")

    writer.writerow([
        "Unidade",
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
            computador.unidade.sigla if computador.unidade else "",
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
    erros = filtrar_erros_agentes(filtros, request.user)
    response = montar_response_csv("erros_agentes.csv")
    writer = csv.writer(response, delimiter=";")

    writer.writerow([
        "Data",
        "Unidade",
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
            erro.unidade.sigla if erro.unidade else "",
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
def patrimonios(request):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    filtros = obter_filtros_patrimonio(request)
    patrimonios_qs = filtrar_patrimonios(filtros, request.user)
    patrimonios_base = aplicar_escopo_unidade(PatrimonioTI.objects.all(), request.user)

    totais = {
        "total": patrimonios_base.count(),
        "em_uso": patrimonios_base.filter(status="em_uso").count(),
        "estoque": patrimonios_base.filter(status="estoque").count(),
        "manutencao": patrimonios_base.filter(status="manutencao").count(),
        "baixados": patrimonios_base.filter(status="baixado").count(),
        "sem_vinculo": patrimonios_base.filter(computador__isnull=True).count(),
        "filtrado": patrimonios_qs.count(),
    }

    query_string = urlencode({
        chave: valor for chave, valor in filtros.items() if valor
    })

    paginator = Paginator(patrimonios_qs, 20)
    pagina = request.GET.get("page")
    patrimonios_pagina = paginator.get_page(pagina)

    return render(request, "inventario_ti/patrimonios.html", {
        "patrimonios": patrimonios_pagina,
        "filtros": filtros,
        "query_string": query_string,
        "totais": totais,
        "tipos": PatrimonioTI.TIPO_CHOICES,
        "status_choices": PatrimonioTI.STATUS_CHOICES,
        "unidades": Unidade.objects.filter(id=obter_unidade_usuario(request.user).id).order_by("nome") if obter_unidade_usuario(request.user) else Unidade.objects.filter(ativo=True).order_by("nome"),
        "setores": Setor.objects.filter(ativo=True).order_by("nome"),
    })


@login_required
def maquinas(request):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    busca = request.GET.get("busca", "").strip()
    setor_id = request.GET.get("setor", "").strip()
    itens = aplicar_escopo_unidade(
        PatrimonioTI.objects.select_related("computador", "unidade", "setor").filter(
            tipo__in=("computador", "notebook"),
            ativo=True,
        ),
        request.user,
    )
    if busca:
        itens = itens.filter(
            Q(codigo__icontains=busca) |
            Q(serial__icontains=busca) |
            Q(modelo__icontains=busca) |
            Q(computador__hostname__icontains=busca) |
            Q(responsavel__icontains=busca)
        )
    if setor_id:
        itens = itens.filter(setor_id=setor_id)

    base = aplicar_escopo_unidade(
        PatrimonioTI.objects.filter(tipo__in=("computador", "notebook"), ativo=True),
        request.user,
    )
    totais = {
        "total": base.count(),
        "computadores": base.filter(tipo="computador").count(),
        "notebooks": base.filter(tipo="notebook").count(),
        "em_uso": base.filter(status="em_uso").count(),
        "estoque": base.filter(status="estoque").count(),
        "manutencao": base.filter(status="manutencao").count(),
        "sem_setor": base.filter(setor__isnull=True).count(),
    }
    pagina = Paginator(itens.order_by("codigo"), 25).get_page(request.GET.get("page"))
    return render(request, "inventario_ti/maquinas.html", {
        "maquinas": pagina,
        "totais": totais,
        "busca": busca,
        "setor_selecionado": setor_id,
        "setores": Setor.objects.filter(ativo=True).order_by("nome"),
    })


@login_required
def suprimentos(request):
    unidade_id = getattr(request.user, "unidade_id", None)
    if not unidade_id:
        return render(request, "core/sem_permissao.html", status=403)

    itens = SuprimentoTI.objects.select_related("unidade", "setor").filter(unidade_id=unidade_id, ativo=True)

    busca = request.GET.get("busca", "").strip()
    categoria = request.GET.get("categoria", "").strip()
    if busca:
        itens = itens.filter(Q(codigo__icontains=busca) | Q(nome__icontains=busca))
    if categoria:
        itens = itens.filter(categoria=categoria)

    lista = list(itens)
    totais = {
        "itens": len(lista),
        "unidades_estoque": sum(item.quantidade for item in lista),
        "estoque_baixo": sum(1 for item in lista if item.quantidade <= LIMITE_ALERTA_SUPRIMENTO),
        "zerados": sum(1 for item in lista if item.quantidade == 0),
    }
    return render(request, "inventario_ti/suprimentos.html", {
        "suprimentos": lista,
        "totais": totais,
        "busca": busca,
        "categoria": categoria,
        "categorias": SuprimentoTI.CATEGORIA_CHOICES,
        "limite_alerta": LIMITE_ALERTA_SUPRIMENTO,
    })


@login_required
def novo_suprimento(request):
    unidade = getattr(request.user, "unidade", None)
    if not unidade:
        return render(request, "core/sem_permissao.html", status=403)

    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        categoria = request.POST.get("categoria", "outro").strip()
        erros = []
        if not nome:
            erros.append("Informe o suprimento.")
        if categoria not in {valor for valor, _rotulo in SuprimentoTI.CATEGORIA_CHOICES}:
            erros.append("Informe uma categoria válida.")
        try:
            quantidade = int(request.POST.get("quantidade", "0"))
        except ValueError:
            quantidade = 0
        if quantidade <= 0:
            erros.append("Informe uma quantidade maior que zero.")

        if not erros:
            with transaction.atomic():
                existente = SuprimentoTI.objects.select_for_update().filter(
                    unidade=unidade,
                    nome__iexact=nome,
                    categoria=categoria,
                    ativo=True,
                ).first()
                if existente:
                    foi_somado = True
                    saldo_anterior = existente.quantidade
                    existente.quantidade += quantidade
                    existente.save(update_fields=["quantidade", "atualizado_em"])
                    item = existente
                else:
                    foi_somado = False
                    saldo_anterior = 0
                    item = SuprimentoTI.objects.create(
                        unidade=unidade,
                        codigo=f"SUP-{uuid.uuid4().hex[:10].upper()}",
                        nome=nome,
                        categoria=categoria,
                        quantidade=quantidade,
                        estoque_minimo=1,
                    )
                MovimentacaoSuprimentoTI.objects.create(
                    suprimento=item, tipo="entrada", quantidade=quantidade,
                    saldo_anterior=saldo_anterior, saldo_atual=item.quantidade, usuario=request.user,
                    observacao="Entrada registrada pelo cadastro de suprimento.",
                )
                sincronizar_alerta_suprimento(item)
            if foi_somado:
                messages.success(request, f"Quantidade adicionada ao item existente. Novo saldo: {item.quantidade}.")
            else:
                messages.success(request, "Suprimento cadastrado com sucesso.")
            return redirect("inventario_ti_suprimentos")
        for erro in erros:
            messages.error(request, erro)

    return render(request, "inventario_ti/formulario_suprimento.html", {
        "categorias": SuprimentoTI.CATEGORIA_CHOICES,
    })


def _suprimento_permitido(user, item):
    return item.unidade_id == getattr(user, "unidade_id", None)


@login_required
def movimentar_suprimento(request, suprimento_id):
    item = get_object_or_404(SuprimentoTI.objects.select_related("unidade", "setor"), id=suprimento_id, ativo=True)
    if not _suprimento_permitido(request.user, item):
        return render(request, "core/sem_permissao.html", status=403)

    if request.method == "POST":
        tipo = request.POST.get("tipo", "").strip()
        try:
            quantidade = int(request.POST.get("quantidade", "0"))
        except ValueError:
            quantidade = 0
        setor_destino = Setor.objects.filter(id=request.POST.get("setor_destino", ""), ativo=True).first()
        erros = []
        if tipo not in {valor for valor, _rotulo in MovimentacaoSuprimentoTI.TIPO_CHOICES}:
            erros.append("Tipo de movimentação inválido.")
        if quantidade <= 0:
            erros.append("Informe uma quantidade maior que zero.")
        if tipo == "saida" and not setor_destino:
            erros.append("Informe o setor que recebeu o material.")

        if not erros:
            with transaction.atomic():
                bloqueado = SuprimentoTI.objects.select_for_update().get(id=item.id)
                saldo_anterior = bloqueado.quantidade
                if tipo == "entrada":
                    saldo_atual = saldo_anterior + quantidade
                elif tipo == "saida":
                    saldo_atual = saldo_anterior - quantidade
                    if saldo_atual < 0:
                        erros.append("A saída não pode ser maior que o saldo disponível.")
                else:
                    saldo_atual = quantidade

                if not erros:
                    bloqueado.quantidade = saldo_atual
                    bloqueado.save(update_fields=["quantidade", "atualizado_em"])
                    MovimentacaoSuprimentoTI.objects.create(
                        suprimento=bloqueado, tipo=tipo, quantidade=quantidade,
                        saldo_anterior=saldo_anterior, saldo_atual=saldo_atual,
                        setor_destino=setor_destino,
                        impressora_destino=request.POST.get("impressora_destino", "").strip(),
                        responsavel=request.POST.get("responsavel", "").strip(),
                        observacao=request.POST.get("observacao", "").strip(),
                        usuario=request.user,
                    )
                    sincronizar_alerta_suprimento(bloqueado)
            if not erros:
                messages.success(request, "Movimentação registrada e saldo atualizado.")
                return redirect("inventario_ti_suprimento_detalhe", suprimento_id=item.id)
        for erro in erros:
            messages.error(request, erro)

    return render(request, "inventario_ti/movimentar_suprimento.html", {
        "item": item,
        "tipos": MovimentacaoSuprimentoTI.TIPO_CHOICES,
        "setores": Setor.objects.filter(ativo=True).order_by("nome"),
    })


@login_required
def detalhe_suprimento(request, suprimento_id):
    item = get_object_or_404(SuprimentoTI.objects.select_related("unidade", "setor"), id=suprimento_id, ativo=True)
    if not _suprimento_permitido(request.user, item):
        return render(request, "core/sem_permissao.html", status=403)
    movimentacoes = item.movimentacoes.select_related("setor_destino", "usuario", "estornada_por")[:100]
    ultima_ativa = item.movimentacoes.filter(estornada_em__isnull=True).order_by("-criado_em").first()
    return render(request, "inventario_ti/detalhe_suprimento.html", {
        "item": item,
        "movimentacoes": movimentacoes,
        "movimentacao_estornavel_id": ultima_ativa.id if ultima_ativa else None,
    })


@login_required
def estornar_movimentacao_suprimento(request, suprimento_id, movimentacao_id):
    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método não permitido"}, status=405)

    item = get_object_or_404(SuprimentoTI, id=suprimento_id, ativo=True)
    if not _suprimento_permitido(request.user, item):
        return render(request, "core/sem_permissao.html", status=403)

    motivo = request.POST.get("motivo", "").strip()
    if not motivo:
        messages.error(request, "Informe o motivo do estorno.")
        return redirect("inventario_ti_suprimento_detalhe", suprimento_id=item.id)

    with transaction.atomic():
        bloqueado = SuprimentoTI.objects.select_for_update().get(id=item.id)
        movimento = get_object_or_404(
            MovimentacaoSuprimentoTI.objects.select_for_update(),
            id=movimentacao_id,
            suprimento=bloqueado,
        )
        ultima_ativa = bloqueado.movimentacoes.filter(estornada_em__isnull=True).order_by("-criado_em").first()
        if movimento.estornada_em:
            messages.error(request, "Esta movimentação já foi estornada.")
        elif not ultima_ativa or ultima_ativa.id != movimento.id:
            messages.error(request, "Somente a movimentação ativa mais recente pode ser estornada.")
        elif bloqueado.quantidade != movimento.saldo_atual:
            messages.error(request, "O saldo atual não corresponde a esta movimentação; revise o histórico.")
        else:
            bloqueado.quantidade = movimento.saldo_anterior
            bloqueado.save(update_fields=["quantidade", "atualizado_em"])
            movimento.estornada_em = timezone.now()
            movimento.estornada_por = request.user
            movimento.motivo_estorno = motivo
            movimento.save(update_fields=["estornada_em", "estornada_por", "motivo_estorno"])
            sincronizar_alerta_suprimento(bloqueado)
            messages.success(request, f"Movimentação estornada. Saldo restaurado para {bloqueado.quantidade}.")

    return redirect("inventario_ti_suprimento_detalhe", suprimento_id=item.id)


@login_required
def movimentar_patrimonio(request, patrimonio_id):
    if not usuario_pode_gerenciar_patrimonio_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    patrimonio = get_object_or_404(
        aplicar_escopo_unidade(PatrimonioTI.objects.select_related("unidade", "setor"), request.user),
        id=patrimonio_id,
    )
    unidades = Unidade.objects.filter(ativo=True).order_by("nome")
    unidade_usuario = obter_unidade_usuario(request.user)
    if not request.user.is_superuser and unidade_usuario:
        unidades = unidades.filter(id=unidade_usuario.id)

    if request.method == "POST":
        unidade_id = request.POST.get("unidade", "").strip()
        setor_id = request.POST.get("setor", "").strip()
        status = request.POST.get("status", "em_uso").strip()
        responsavel = request.POST.get("responsavel", "").strip()
        observacao = request.POST.get("observacao", "").strip()
        unidade_destino = unidades.filter(id=unidade_id).first()
        setor_destino = Setor.objects.filter(id=setor_id, ativo=True).first() if setor_id else None
        status_validos = {valor for valor, _rotulo in PatrimonioTI.STATUS_CHOICES}
        erros = []
        if not unidade_destino:
            erros.append("Selecione uma unidade permitida.")
        if status not in status_validos:
            erros.append("Selecione um status válido.")
        if not observacao:
            erros.append("Informe o motivo da movimentação.")

        if not erros:
            origem = snapshot_origem_patrimonio(patrimonio)
            patrimonio.unidade = unidade_destino
            patrimonio.setor = setor_destino
            patrimonio.status = status
            patrimonio.responsavel = responsavel
            patrimonio.save(update_fields=["unidade", "setor", "status", "responsavel", "atualizado_em"])
            tipo = "manutencao" if status == "manutencao" else "transferencia"
            registrar_movimentacao_patrimonio(
                patrimonio=patrimonio,
                tipo=tipo,
                usuario=request.user,
                observacao=observacao,
                origem=origem,
            )
            messages.success(request, "Máquina movimentada e histórico atualizado.")
            return redirect("inventario_ti_patrimonio_detalhe", patrimonio_id=patrimonio.id)

        for erro in erros:
            messages.error(request, erro)

    return render(request, "inventario_ti/movimentar_patrimonio.html", {
        "patrimonio": patrimonio,
        "unidades": unidades,
        "setores": Setor.objects.filter(ativo=True).order_by("nome"),
        "status_choices": PatrimonioTI.STATUS_CHOICES,
    })

@login_required
def modelo_importacao_patrimonios(request):
    if not usuario_pode_gerenciar_patrimonio_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    response = montar_response_csv("modelo_importacao_patrimonios.csv")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(COLUNAS_IMPORTACAO_PATRIMONIO)
    writer.writerow(["PAT-0001", "computador", "em_uso", "HSFOS", "TI", "", "Dell", "OptiPlex", "SERIAL-EXEMPLO", ""])
    return response


@login_required
def importar_patrimonios(request):
    if not usuario_pode_gerenciar_patrimonio_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            messages.error(request, "Selecione um arquivo CSV.")
        else:
            try:
                linhas = ler_csv_patrimonios(arquivo)
                preparados, erros = validar_linhas_importacao_patrimonio(linhas, request.user)
                if not preparados and not erros:
                    erros.append("O arquivo não possui registros para importar.")

                if erros:
                    for erro in erros[:20]:
                        messages.error(request, erro)
                    if len(erros) > 20:
                        messages.error(request, f"Existem mais {len(erros) - 20} erro(s) no arquivo.")
                else:
                    with transaction.atomic():
                        for dados in preparados:
                            patrimonio = PatrimonioTI.objects.create(**dados)
                            registrar_movimentacao_patrimonio(
                                patrimonio=patrimonio, tipo="cadastro", usuario=request.user,
                                observacao="Patrimônio importado por CSV.",
                            )
                    unidades_importadas = {dados["unidade"].id for dados in preparados if dados["unidade"]}
                    vinculados = reconciliar_patrimonios_por_serial(unidades_importadas)
                    messages.success(
                        request,
                        f"{len(preparados)} patrimônio(s) importado(s) e "
                        f"{len(vinculados)} vínculo(s) automático(s) realizado(s).",
                    )
                    return redirect("inventario_ti_patrimonios")
            except (UnicodeError, csv.Error, ValueError) as erro:
                messages.error(request, str(erro))

    return render(request, "inventario_ti/importar_patrimonios.html")


@login_required
def novo_patrimonio(request):
    if not usuario_pode_gerenciar_patrimonio_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    form_data = {
        "codigo": "",
        "tipo": request.GET.get("tipo", "computador") if request.GET.get("tipo", "computador") in {valor for valor, _rotulo in PatrimonioTI.TIPO_CHOICES} else "computador",
        "status": "em_uso",
        "computador": "",
        "unidade": "",
        "setor": "",
        "responsavel": "",
        "fabricante": "",
        "modelo": "",
        "serial": "",
        "nota_fiscal": "",
        "data_aquisicao": "",
        "valor_aquisicao": "",
        "observacao": "",
        "ativo": True,
    }
    form_data = aplicar_unidade_usuario_form_data(form_data, request.user)

    if request.method == "POST":
        form_data = aplicar_unidade_usuario_form_data(montar_form_data_patrimonio(request), request.user)
        erros = []

        if not form_data["codigo"]:
            erros.append("Informe o código do patrimônio.")

        if PatrimonioTI.objects.filter(codigo=form_data["codigo"]).exists():
            erros.append("Já existe um patrimônio com este código.")

        if not computador_pode_ser_vinculado(form_data["computador"], request.user):
            erros.append("O computador selecionado não pertence à sua unidade.")

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, "inventario_ti/formulario_patrimonio.html", {
                **contexto_formulario_patrimonio(form_data, user=request.user),
                "titulo": "Novo patrimônio",
                "modo": "novo",
            })

        patrimonio = PatrimonioTI()
        aplicar_form_data_patrimonio(patrimonio, form_data)
        patrimonio.save()
        sincronizar_patrimonio_computador(patrimonio)
        registrar_movimentacao_patrimonio(
            patrimonio=patrimonio,
            tipo="cadastro",
            usuario=request.user,
            observacao="Patrimônio cadastrado.",
        )
        messages.success(request, "Patrimônio cadastrado com sucesso.")
        return redirect("inventario_ti_patrimonio_detalhe", patrimonio_id=patrimonio.id)

    return render(request, "inventario_ti/formulario_patrimonio.html", {
        **contexto_formulario_patrimonio(form_data, user=request.user),
        "titulo": "Novo patrimônio",
        "modo": "novo",
    })


@login_required
def editar_patrimonio(request, patrimonio_id):
    if not usuario_pode_gerenciar_patrimonio_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    patrimonio = get_object_or_404(
        aplicar_escopo_unidade(PatrimonioTI.objects.all(), request.user),
        id=patrimonio_id,
    )
    form_data = patrimonio_para_form_data(patrimonio)

    if request.method == "POST":
        computador_anterior_id = patrimonio.computador_id
        origem = snapshot_origem_patrimonio(patrimonio)
        form_data = aplicar_unidade_usuario_form_data(montar_form_data_patrimonio(request), request.user)
        erros = []

        if not form_data["codigo"]:
            erros.append("Informe o código do patrimônio.")

        if PatrimonioTI.objects.filter(codigo=form_data["codigo"]).exclude(id=patrimonio.id).exists():
            erros.append("Já existe outro patrimônio com este código.")

        if not computador_pode_ser_vinculado(form_data["computador"], request.user):
            erros.append("O computador selecionado não pertence à sua unidade.")

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, "inventario_ti/formulario_patrimonio.html", {
                **contexto_formulario_patrimonio(form_data, patrimonio, request.user),
                "titulo": "Editar patrimônio",
                "modo": "editar",
            })

        aplicar_form_data_patrimonio(patrimonio, form_data)
        patrimonio.save()
        sincronizar_patrimonio_computador(patrimonio, computador_anterior_id)
        registrar_movimentacao_patrimonio(
            patrimonio=patrimonio,
            tipo="ajuste",
            usuario=request.user,
            observacao="Patrimônio atualizado.",
            origem=origem,
        )
        messages.success(request, "Patrimônio atualizado com sucesso.")
        return redirect("inventario_ti_patrimonio_detalhe", patrimonio_id=patrimonio.id)

    return render(request, "inventario_ti/formulario_patrimonio.html", {
        **contexto_formulario_patrimonio(form_data, patrimonio, request.user),
        "titulo": "Editar patrimônio",
        "modo": "editar",
    })


@login_required
def detalhe_patrimonio(request, patrimonio_id):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    patrimonio = get_object_or_404(
        aplicar_escopo_unidade(
            PatrimonioTI.objects.select_related("computador", "unidade", "setor"),
            request.user,
        ),
        id=patrimonio_id,
    )
    movimentacoes = patrimonio.movimentacoes.select_related(
        "unidade_origem",
        "setor_origem",
        "unidade_destino",
        "setor_destino",
        "usuario",
    )[:20]

    return render(request, "inventario_ti/detalhe_patrimonio.html", {
        "patrimonio": patrimonio,
        "movimentacoes": movimentacoes,
    })


def _obter_patrimonio_autorizado(request, patrimonio_id):
    return get_object_or_404(
        aplicar_escopo_unidade(PatrimonioTI.objects.select_related("unidade", "setor"), request.user),
        id=patrimonio_id,
    )


@login_required
def qr_patrimonio(request, patrimonio_id):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return HttpResponse(status=403)
    patrimonio = _obter_patrimonio_autorizado(request, patrimonio_id)
    detalhe_url = request.build_absolute_uri(
        reverse("inventario_ti_patrimonio_detalhe", args=[patrimonio.id])
    )
    imagem = qrcode.make(detalhe_url, image_factory=SvgPathImage, box_size=8, border=2)
    arquivo = BytesIO()
    imagem.save(arquivo)
    resposta = HttpResponse(arquivo.getvalue(), content_type="image/svg+xml")
    resposta["Cache-Control"] = "private, max-age=300"
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta


@login_required
def etiqueta_patrimonio(request, patrimonio_id):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)
    patrimonio = _obter_patrimonio_autorizado(request, patrimonio_id)
    return render(request, "inventario_ti/etiqueta_patrimonio.html", {"patrimonio": patrimonio})


@login_required
def detalhe(request, computador_id):
    if not usuario_pode_acessar_inventario_ti(request.user):
        return render(request, "core/sem_permissao.html", status=403)

    computador = get_object_or_404(
        aplicar_escopo_unidade(ComputadorInventario.objects.all(), request.user),
        id=computador_id,
    )
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
        ("Unidade", computador.unidade.nome if computador.unidade else "-"),
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
