from django.utils import timezone

from avisos.models import AvisoComunicado
from solicitacoes_ti.models import SolicitacaoTI

try:
    from inventario_ti.models import ComputadorInventario
except Exception:
    ComputadorInventario = None


NOTIFICACAO_INFO = "info"
NOTIFICACAO_SUCESSO = "success"
NOTIFICACAO_ALERTA = "warning"
NOTIFICACAO_CRITICA = "danger"


def criar_notificacao(
    titulo,
    descricao="",
    tipo=NOTIFICACAO_INFO,
    link=None,
    icone="🔔",
):
    return {
        "titulo": titulo,
        "descricao": descricao,
        "tipo": tipo,
        "icone": icone,
        "link": link,
        "data": timezone.now(),
    }


def notificacoes_chamados():
    notificacoes = []

    chamados = (
        SolicitacaoTI.objects
        .filter(
            ativo=True,
            prioridade="critica",
        )
        .exclude(status__in=["resolvido", "cancelado"])
        .order_by("-criado_em")[:5]
    )

    for chamado in chamados:
        notificacoes.append(
            criar_notificacao(
                titulo=f"Chamado crítico #{chamado.id}",
                descricao=chamado.titulo,
                tipo=NOTIFICACAO_CRITICA,
                icone="🚨",
                link="/portal/modulos/solicitacoes-ti/",
            )
        )

    return notificacoes


def notificacoes_inventario():
    if ComputadorInventario is None:
        return []

    notificacoes = []

    computadores = (
        ComputadorInventario.objects
        .exclude(ultimo_contato__isnull=True)
        .order_by("-ultimo_contato")[:100]
    )

    for computador in computadores:
        if computador.online:
            continue

        notificacoes.append(
            criar_notificacao(
                titulo=f"{computador.hostname} offline",
                descricao="Heartbeat não recebido recentemente.",
                tipo=NOTIFICACAO_ALERTA,
                icone="🖥️",
                link="/portal/modulos/inventario-ti/",
            )
        )

        if len(notificacoes) >= 5:
            break

    return notificacoes


def notificacoes_avisos():
    notificacoes = []

    avisos = (
        AvisoComunicado.objects
        .filter(
            ativo=True,
            exibir_no_dashboard=True,
        )
        .order_by("-publicado_em")[:3]
    )

    for aviso in avisos:
        notificacoes.append(
            criar_notificacao(
                titulo=aviso.titulo,
                descricao="Novo comunicado.",
                tipo=NOTIFICACAO_INFO,
                icone="📢",
                link="/portal/",
            )
        )

    return notificacoes


def listar_notificacoes():
    notificacoes = []

    notificacoes.extend(notificacoes_chamados())
    notificacoes.extend(notificacoes_inventario())
    notificacoes.extend(notificacoes_avisos())

    notificacoes.sort(
        key=lambda notificacao: notificacao["data"],
        reverse=True
    )

    return notificacoes[:15]