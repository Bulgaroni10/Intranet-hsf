from django import template
from django.db.models import Q

from modulos.models import Modulo
from solicitacoes_ti.models import SolicitacaoTI


register = template.Library()


def usuario_eh_admin_ti(user):
    if not user or not user.is_authenticated:
        return False

    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def usuario_eh_ti(user):
    if not user or not user.is_authenticated:
        return False

    return usuario_eh_admin_ti(user) or user.groups.filter(
        name__in=['TI Suporte', 'TI']
    ).exists()


@register.simple_tag
def usuario_eh_admin_ti_tag(user):
    return usuario_eh_admin_ti(user)


@register.simple_tag
def usuario_pode_ver_inventario_ti(user):
    return usuario_eh_ti(user)


@register.simple_tag
def pode_acessar_modulo_link(user, link_modulo):
    return usuario_pode_acessar_modulo_por_link(user, link_modulo)


def usuario_pode_acessar_modulo_por_link(user, link_modulo):
    if usuario_eh_admin_ti(user):
        return True

    try:
        modulo = Modulo.objects.get(link=link_modulo, ativo=True)
    except Modulo.DoesNotExist:
        return False

    if not modulo.grupos_permitidos.exists():
        return True

    return modulo.grupos_permitidos.filter(
        id__in=user.groups.values_list('id', flat=True)
    ).exists()


def usuario_pode_acessar_modulo_por_nome(user, nome_modulo):
    if usuario_eh_admin_ti(user):
        return True

    try:
        modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    except Modulo.DoesNotExist:
        return False

    if not modulo.grupos_permitidos.exists():
        return True

    return modulo.grupos_permitidos.filter(
        id__in=user.groups.values_list('id', flat=True)
    ).exists()


def usuario_pode_acessar_solicitacoes_ti(user):
    if not user or not user.is_authenticated:
        return False

    if usuario_eh_admin_ti(user):
        return True

    links_possiveis = [
        '/portal/modulos/solicitacoes-ti/',
        '/portal/modulos/solicitacoes-ti',
    ]

    nomes_possiveis = [
        'Solicitações de TI',
        'Solicitações Internas de TI',
        'Solicitações TI',
        'Chamados de TI',
        'Solicitações Internas',
    ]

    for link in links_possiveis:
        if usuario_pode_acessar_modulo_por_link(user, link):
            return True

    for nome in nomes_possiveis:
        if usuario_pode_acessar_modulo_por_nome(user, nome):
            return True

    return False


def atualizar_sla_solicitacoes(solicitacoes):
    for solicitacao in solicitacoes:
        if hasattr(solicitacao, 'atualizar_sla'):
            try:
                solicitacao.atualizar_sla(salvar=True)
            except Exception:
                pass


@register.simple_tag
def painel_ti_dashboard(user, limite=8):
    dados = {
        'pode_acessar': False,
        'total': 0,
        'abertos': 0,
        'em_atendimento': 0,
        'aguardando': 0,
        'resolvidos': 0,
        'sla_alerta': 0,
        'sla_estourado': 0,
        'sem_responsavel': 0,
        'criticos': 0,
        'ativos_total': 0,
        'ultimos': SolicitacaoTI.objects.none(),
    }

    if not user or not user.is_authenticated:
        return dados

    pode_acessar = usuario_pode_acessar_solicitacoes_ti(user)

    if not pode_acessar:
        return dados

    dados['pode_acessar'] = True

    chamados_base = SolicitacaoTI.objects.filter(
        ativo=True
    )

    if not usuario_eh_admin_ti(user):
        chamados_base = chamados_base.filter(
            solicitante=user
        )

    chamados_ativos = chamados_base.exclude(
        status__in=['resolvido', 'cancelado']
    )

    chamados_para_atualizar_sla = chamados_ativos.order_by(
        '-criado_em'
    )[:100]

    atualizar_sla_solicitacoes(chamados_para_atualizar_sla)

    chamados_base = SolicitacaoTI.objects.filter(
        ativo=True
    )

    if not usuario_eh_admin_ti(user):
        chamados_base = chamados_base.filter(
            solicitante=user
        )

    chamados_ativos = chamados_base.exclude(
        status__in=['resolvido', 'cancelado']
    )

    dados['total'] = chamados_base.count()
    dados['abertos'] = chamados_base.filter(status='aberto').count()
    dados['em_atendimento'] = chamados_base.filter(status='em_atendimento').count()
    dados['aguardando'] = chamados_base.filter(
        Q(status='aguardando_usuario') |
        Q(status='aguardando_terceiro')
    ).count()
    dados['resolvidos'] = chamados_base.filter(status='resolvido').count()
    dados['sla_alerta'] = chamados_ativos.filter(sla_status='proximo_vencimento').count()
    dados['sla_estourado'] = chamados_ativos.filter(sla_status='estourado').count()
    dados['sem_responsavel'] = chamados_ativos.filter(responsavel_ti__isnull=True).count()
    dados['criticos'] = chamados_ativos.filter(prioridade='critica').count()
    dados['ativos_total'] = chamados_ativos.count()

    dados['ultimos'] = chamados_base.select_related(
        'unidade',
        'setor',
        'solicitante',
        'responsavel_ti'
    ).order_by(
        '-criado_em'
    )[:limite]

    return dados
