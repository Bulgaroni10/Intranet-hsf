from django.utils import timezone


EVENTO_INFO = "info"
EVENTO_SUCESSO = "success"
EVENTO_ALERTA = "warning"
EVENTO_CRITICO = "danger"


def criar_evento_memoria(
    titulo,
    descricao="",
    tipo=EVENTO_INFO,
    origem="sistema",
    icone="ℹ️",
    link=None,
    data=None,
):
    return {
        "titulo": titulo,
        "descricao": descricao,
        "tipo": tipo,
        "origem": origem,
        "icone": icone,
        "link": link,
        "data": data or timezone.now(),
    }


def eventos_inventario(computadores):
    eventos = []

    for pc in computadores:
        if not pc.ultimo_contato:
            continue

        if pc.online:
            eventos.append(
                criar_evento_memoria(
                    titulo=f"{pc.hostname} online",
                    descricao=f"Último contato registrado em {pc.ultimo_contato:%d/%m/%Y %H:%M}",
                    tipo=EVENTO_SUCESSO,
                    origem="Inventário TI",
                    icone="🟢",
                    link=f"/portal/modulos/inventario-ti/{pc.id}/",
                    data=pc.ultimo_contato,
                )
            )
        else:
            eventos.append(
                criar_evento_memoria(
                    titulo=f"{pc.hostname} offline",
                    descricao=f"Sem heartbeat recente. Último contato em {pc.ultimo_contato:%d/%m/%Y %H:%M}",
                    tipo=EVENTO_ALERTA,
                    origem="Inventário TI",
                    icone="🔴",
                    link=f"/portal/modulos/inventario-ti/{pc.id}/",
                    data=pc.ultimo_contato,
                )
            )

    return eventos


def eventos_chamados_ti(chamados):
    eventos = []

    for chamado in chamados:
        tipo = EVENTO_INFO
        icone = "📋"

        if getattr(chamado, "prioridade", "") == "critica":
            tipo = EVENTO_CRITICO
            icone = "🚨"

        eventos.append(
            criar_evento_memoria(
                titulo=f"Solicitação TI #{chamado.id}",
                descricao=chamado.titulo,
                tipo=tipo,
                origem="Solicitações TI",
                icone=icone,
                link=f"/portal/modulos/solicitacoes-ti/?busca={chamado.id}",
                data=chamado.criado_em,
            )
        )

    return eventos


def eventos_ocorrencias(ocorrencias):
    eventos = []

    for ocorrencia in ocorrencias:
        eventos.append(
            criar_evento_memoria(
                titulo=f"Ocorrência: {ocorrencia.titulo}",
                descricao=ocorrencia.sistema.nome if ocorrencia.sistema else "",
                tipo=EVENTO_ALERTA,
                origem="Status dos Sistemas",
                icone="📡",
                link="/portal/modulos/status-sistemas/",
                data=ocorrencia.atualizado_em,
            )
        )

    return eventos


def montar_timeline_global(
    computadores=None,
    chamados_ti=None,
    ocorrencias=None,
    limite=10,
):
    eventos = []

    if computadores:
        eventos.extend(eventos_inventario(computadores))

    if chamados_ti:
        eventos.extend(eventos_chamados_ti(chamados_ti))

    if ocorrencias:
        eventos.extend(eventos_ocorrencias(ocorrencias))

    eventos.sort(
        key=lambda evento: evento["data"],
        reverse=True
    )

    return eventos[:limite]