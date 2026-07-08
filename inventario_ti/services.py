from django.utils import timezone

from .models import ComputadorInventario, ErroAgenteInventario, HistoricoComputadorInventario


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
