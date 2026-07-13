from django.db import transaction
from django.utils import timezone
import re

from .models import (
    ComputadorInventario,
    ErroAgenteInventario,
    HistoricoComputadorInventario,
    MovimentacaoPatrimonioTI,
    PatrimonioTI,
)


CAMPOS_MONITORADOS = {
    "usuario": "Usuário logado",
    "ip_origem": "IP origem",
    "ip_local": "IP local",
    "mac": "MAC",
    "sistema": "Sistema operacional",
    "cpu": "CPU",
    "ram": "RAM",
    "disco_total": "Disco total",
    "disco_livre": "Disco livre",
    "disco_percentual": "Uso do disco",
    "fabricante": "Fabricante",
    "modelo": "Modelo",
    "serial": "Serial",
    "patrimonio": "Patrimônio",
    "agent_version": "Versão do agente",
}


def normalizar_valor(valor):
    if valor is None:
        return ""

    return str(valor).strip()


SERIAIS_INVALIDOS = {"", "-", "NONE", "NULL", "UNKNOWN", "TO BE FILLED BY O.E.M."}


def codigo_patrimonio_hostname(hostname):
    codigo = re.sub(r"\s+", "", normalizar_valor(hostname)).upper()
    return codigo if re.fullmatch(r"P0{2,}\d+", codigo) else ""


def vincular_patrimonio_por_hostname(computador):
    """Usa hostnames patrimoniais P000... quando o agente ainda não possui vínculo."""
    codigo = codigo_patrimonio_hostname(computador.hostname)
    if not codigo or not computador.unidade_id or PatrimonioTI.objects.filter(computador=computador).exists():
        return None

    with transaction.atomic():
        patrimonio = PatrimonioTI.objects.select_for_update().filter(codigo__iexact=codigo).first()
        if patrimonio and patrimonio.unidade_id != computador.unidade_id:
            return None
        if patrimonio and patrimonio.computador_id not in (None, computador.id):
            return None

        criado = patrimonio is None
        if criado:
            patrimonio = PatrimonioTI.objects.create(
                codigo=codigo,
                tipo="computador",
                status="em_uso",
                computador=computador,
                unidade=computador.unidade,
                fabricante="" if computador.fabricante == "-" else computador.fabricante,
                modelo="" if computador.modelo == "-" else computador.modelo,
                serial="" if computador.serial == "-" else computador.serial,
                observacao="Cadastro criado automaticamente pelo agente a partir do hostname patrimonial.",
            )
        else:
            patrimonio.computador = computador
            patrimonio.save(update_fields=["computador", "atualizado_em"])

        ComputadorInventario.objects.filter(pk=computador.pk).update(patrimonio=codigo)
        computador.patrimonio = codigo
        MovimentacaoPatrimonioTI.objects.create(
            patrimonio=patrimonio,
            tipo="cadastro" if criado else "ajuste",
            unidade_destino=computador.unidade,
            observacao=f"Vínculo automático ao computador {computador.hostname} pelo hostname patrimonial.",
        )
        registrar_evento(
            computador=computador,
            tipo="alteracao",
            titulo="Patrimônio identificado pelo hostname",
            descricao=f"Ativo {codigo} vinculado automaticamente pelo agente.",
            campo="patrimonio",
            valor_anterior="-",
            valor_novo=codigo,
            dados={"patrimonio_id": patrimonio.id, "criterio": "hostname"},
        )
        return patrimonio


def vincular_patrimonio_por_serial(computador):
    """Vincula somente quando o serial identifica um unico ativo livre na unidade."""
    serial = normalizar_valor(computador.serial)
    if serial.upper() in SERIAIS_INVALIDOS or not computador.unidade_id:
        return None

    with transaction.atomic():
        candidatos = list(
            PatrimonioTI.objects.select_for_update()
            .filter(
                serial__iexact=serial,
                unidade_id=computador.unidade_id,
                tipo__in=("computador", "notebook"),
                ativo=True,
            )[:2]
        )
        if len(candidatos) != 1:
            return None

        patrimonio = candidatos[0]
        if patrimonio.computador_id == computador.id:
            if computador.patrimonio != patrimonio.codigo:
                ComputadorInventario.objects.filter(pk=computador.pk).update(patrimonio=patrimonio.codigo)
                computador.patrimonio = patrimonio.codigo
            return patrimonio

        if patrimonio.computador_id is not None:
            return None

        patrimonio.computador = computador
        patrimonio.save(update_fields=["computador", "atualizado_em"])
        ComputadorInventario.objects.filter(pk=computador.pk).update(patrimonio=patrimonio.codigo)
        computador.patrimonio = patrimonio.codigo

        MovimentacaoPatrimonioTI.objects.create(
            patrimonio=patrimonio,
            tipo="ajuste",
            unidade_destino=patrimonio.unidade,
            setor_destino=patrimonio.setor,
            responsavel_destino=patrimonio.responsavel,
            observacao=(
                f"Vinculo automatico ao computador {computador.hostname} "
                f"pelo numero de serie {serial}."
            ),
        )
        registrar_evento(
            computador=computador,
            tipo="alteracao",
            titulo="Patrimonio vinculado automaticamente",
            descricao=f"Ativo {patrimonio.codigo} identificado pelo numero de serie.",
            campo="patrimonio",
            valor_anterior="-",
            valor_novo=patrimonio.codigo,
            dados={"patrimonio_id": patrimonio.id, "criterio": "serial"},
        )
        return patrimonio


def reconciliar_patrimonios_por_serial(unidade_ids=None):
    """Concilia o estoque existente sem arriscar seriais repetidos entre computadores."""
    computadores = ComputadorInventario.objects.filter(
        patrimonio_vinculado__isnull=True,
        patrimonio__in=("", "-"),
    ).select_related("unidade")
    if unidade_ids:
        computadores = computadores.filter(unidade_id__in=set(unidade_ids))

    computadores_por_chave = {}
    for computador in computadores:
        serial = normalizar_valor(computador.serial)
        if serial.upper() in SERIAIS_INVALIDOS or not computador.unidade_id:
            continue
        chave = (computador.unidade_id, serial.casefold())
        computadores_por_chave.setdefault(chave, []).append(computador)

    vinculados = []
    for candidatos in computadores_por_chave.values():
        if len(candidatos) != 1:
            continue
        patrimonio = vincular_patrimonio_por_serial(candidatos[0])
        if patrimonio:
            vinculados.append(patrimonio)

    return vinculados


def computador_estava_offline(computador):
    if not computador or not computador.ultimo_contato:
        return True

    limite = timezone.now() - timezone.timedelta(seconds=90)
    return computador.ultimo_contato < limite


def registrar_evento(computador, tipo, titulo, descricao="", campo="", valor_anterior="", valor_novo="", dados=None):
    return HistoricoComputadorInventario.objects.create(
        computador=computador,
        tipo=tipo,
        titulo=titulo,
        descricao=descricao,
        campo=campo,
        valor_anterior=normalizar_valor(valor_anterior),
        valor_novo=normalizar_valor(valor_novo),
        dados=dados or {},
    )


def registrar_cadastro_computador(computador):
    registrar_evento(
        computador=computador,
        tipo="cadastro",
        titulo="Computador cadastrado no inventário",
        descricao="Primeiro heartbeat recebido pelo GSF Hub.",
        dados={campo: normalizar_valor(getattr(computador, campo, "")) for campo in CAMPOS_MONITORADOS},
    )


def registrar_retorno_online(computador, ultimo_contato_anterior):
    registrar_evento(
        computador=computador,
        tipo="status",
        titulo="Computador voltou a ficar online",
        descricao="A máquina enviou heartbeat após estar fora da janela de online.",
        campo="ultimo_contato",
        valor_anterior=ultimo_contato_anterior,
        valor_novo=computador.ultimo_contato,
    )


def registrar_alteracoes_inventario(computador, valores_anteriores, novos_valores):
    eventos = []

    for campo, rotulo in CAMPOS_MONITORADOS.items():
        anterior = normalizar_valor(valores_anteriores.get(campo))
        novo = normalizar_valor(novos_valores.get(campo))

        if anterior == novo:
            continue

        eventos.append(HistoricoComputadorInventario(
            computador=computador,
            tipo="alteracao",
            titulo=f"{rotulo} alterado",
            descricao=f"Campo {rotulo} atualizado pelo heartbeat do agente.",
            campo=campo,
            valor_anterior=anterior,
            valor_novo=novo,
            dados={"rotulo": rotulo},
        ))

    if eventos:
        HistoricoComputadorInventario.objects.bulk_create(eventos)

    return eventos


def registrar_erro_agente(dados, ip_origem=None, unidade=None):
    hostname = normalizar_valor(dados.get("hostname")).upper() or "-"
    computadores = ComputadorInventario.objects.filter(hostname=hostname)

    if unidade:
        computadores = computadores.filter(unidade=unidade)

    computador = computadores.first()

    erro = ErroAgenteInventario.objects.create(
        computador=computador,
        unidade=unidade or (computador.unidade if computador else None),
        hostname=hostname,
        agent_version=normalizar_valor(dados.get("agent_version")) or "-",
        categoria=normalizar_valor(dados.get("categoria")) or "geral",
        mensagem=normalizar_valor(dados.get("mensagem")) or "Erro sem mensagem.",
        detalhe=normalizar_valor(dados.get("detalhe")),
        payload=dados.get("payload") or {},
        ip_origem=ip_origem,
    )

    if computador:
        registrar_evento(
            computador=computador,
            tipo="status",
            titulo=f"Erro do agente: {erro.categoria}",
            descricao=erro.mensagem,
            campo="agent_error",
            valor_novo=str(erro.id),
            dados={
                "erro_id": erro.id,
                "categoria": erro.categoria,
                "agent_version": erro.agent_version,
            },
        )

    return erro
