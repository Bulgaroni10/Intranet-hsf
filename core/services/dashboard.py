from django.db.models import Q
from django.utils import timezone

from avisos.models import AvisoComunicado
from conteudos.models import ConteudoModulo
from documentos.models import DocumentoProtocolo
from modulos.models import Modulo
from solicitacoes_ti.models import SolicitacaoTI
from status_sistemas.models import OcorrenciaSistema

from core.services.events import montar_timeline_global
from core.services.favorites import listar_favoritos
from core.services.permissions import (
    usuario_eh_admin_ti,
    usuario_eh_gestao,
    usuario_eh_ti,
    usuario_pode_acessar_modulo_por_nome,
    usuario_pode_acessar_solicitacoes_ti,
)

try:
    from inventario_ti.models import ComputadorInventario
except Exception:
    ComputadorInventario = None


def obter_unidade_usuario(user):
    return getattr(user, "unidade", None)


def buscar_resumo_inventario_ti():
    if ComputadorInventario is None:
        return {
            "total_computadores": 0,
            "total_computadores_online": 0,
            "total_computadores_offline": 0,
            "total_computadores_sem_patrimonio": 0,
            "ultimos_computadores": [],
        }

    computadores = list(ComputadorInventario.objects.all())

    total = len(computadores)
    online = len([pc for pc in computadores if pc.online])
    offline = total - online
    sem_patrimonio = len([
        pc for pc in computadores
        if not pc.patrimonio or pc.patrimonio == "-"
    ])

    return {
        "total_computadores": total,
        "total_computadores_online": online,
        "total_computadores_offline": offline,
        "total_computadores_sem_patrimonio": sem_patrimonio,
        "ultimos_computadores": ComputadorInventario.objects.order_by("-ultimo_contato")[:6],
    }


def buscar_avisos_dashboard(user):
    agora = timezone.now()
    unidade_usuario = obter_unidade_usuario(user)

    avisos = AvisoComunicado.objects.filter(
        ativo=True,
        exibir_no_dashboard=True,
        publicado_em__lte=agora,
    ).filter(
        Q(expira_em__isnull=True) |
        Q(expira_em__gte=agora)
    )

    if usuario_eh_admin_ti(user):
        return avisos.select_related(
            "unidade",
            "criado_por"
        ).prefetch_related(
            "grupos_permitidos",
            "unidades_compartilhadas"
        ).order_by(
            "-fixar_no_topo",
            "-publicado_em",
            "titulo"
        )[:5]

    avisos = avisos.filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=unidade_usuario)
    )

    grupos_usuario = user.groups.all()

    return avisos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().select_related(
        "unidade",
        "criado_por"
    ).prefetch_related(
        "grupos_permitidos",
        "unidades_compartilhadas"
    ).order_by(
        "-fixar_no_topo",
        "-publicado_em",
        "titulo"
    )[:5]


def buscar_documentos_dashboard(user):
    hoje = timezone.localdate()
    limite_30_dias = hoje + timezone.timedelta(days=30)
    unidade_usuario = obter_unidade_usuario(user)
    setor_usuario = getattr(user, "setor", None)

    documentos = DocumentoProtocolo.objects.filter(
        ativo=True,
        exibir_no_dashboard=True,
    ).exclude(
        status="inativo"
    ).filter(
        Q(status="em_revisao") |
        Q(data_validade__isnull=False, data_validade__lt=hoje) |
        Q(
            data_validade__isnull=False,
            data_validade__gte=hoje,
            data_validade__lte=limite_30_dias
        )
    )

    if usuario_eh_admin_ti(user):
        return documentos.select_related(
            "unidade",
            "setor",
            "criado_por"
        ).prefetch_related(
            "grupos_permitidos",
            "unidades_compartilhadas"
        ).order_by(
            "data_validade",
            "titulo"
        )[:6]

    documentos = documentos.filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=unidade_usuario)
    ).filter(
        Q(setor=setor_usuario) |
        Q(setor__isnull=True)
    )

    grupos_usuario = user.groups.all()

    return documentos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().select_related(
        "unidade",
        "setor",
        "criado_por"
    ).prefetch_related(
        "grupos_permitidos",
        "unidades_compartilhadas"
    ).order_by(
        "data_validade",
        "titulo"
    )[:6]


def buscar_conteudos_permitidos(user, modulo):
    unidade_usuario = obter_unidade_usuario(user)

    conteudos = ConteudoModulo.objects.filter(
        modulo=modulo,
        ativo=True
    ).filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True)
    )

    if usuario_eh_admin_ti(user):
        return conteudos.order_by("tipo", "ordem", "titulo")

    grupos_usuario = user.groups.all()

    return conteudos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().order_by("tipo", "ordem", "titulo")


def buscar_links_rapidos(user):
    try:
        modulo_links = Modulo.objects.get(
            nome="Links Úteis / Sistemas Internos",
            ativo=True
        )
    except Modulo.DoesNotExist:
        return ConteudoModulo.objects.none()

    if not usuario_pode_acessar_modulo_por_nome(user, modulo_links.nome):
        return ConteudoModulo.objects.none()

    return buscar_conteudos_permitidos(
        user,
        modulo_links
    ).filter(
        tipo="link"
    ).select_related(
        "unidade"
    ).order_by(
        "ordem",
        "titulo"
    )[:6]


def buscar_ultimos_manuais(user):
    try:
        modulo_manuais = Modulo.objects.get(
            nome="Manuais e Procedimentos",
            ativo=True
        )
    except Modulo.DoesNotExist:
        return ConteudoModulo.objects.none()

    if not usuario_pode_acessar_modulo_por_nome(user, modulo_manuais.nome):
        return ConteudoModulo.objects.none()

    return buscar_conteudos_permitidos(
        user,
        modulo_manuais
    ).select_related(
        "unidade"
    ).order_by(
        "-atualizado_em",
        "titulo"
    )[:5]


def atualizar_sla_solicitacoes_dashboard(solicitacoes):
    for solicitacao in solicitacoes:
        if hasattr(solicitacao, "atualizar_sla"):
            solicitacao.atualizar_sla(salvar=True)


def filtrar_chamados_ti_dashboard(user, queryset):
    """Aplica a mesma visibilidade à lista e a todos os contadores do dashboard."""
    if user.is_superuser:
        return queryset

    unidade = obter_unidade_usuario(user)
    if unidade is None:
        return queryset.none()

    if usuario_eh_ti(user) or usuario_eh_gestao(user):
        return queryset.filter(unidade=unidade)

    return queryset.filter(solicitante=user)


def buscar_resumo_chamados_ti(user, limite=8, modulo_origem=None):
    chamados_base = SolicitacaoTI.objects.filter(
        ativo=True
    )

    if modulo_origem:
        chamados_base = chamados_base.filter(
            modulo_origem=modulo_origem
        )

    chamados_base = filtrar_chamados_ti_dashboard(user, chamados_base)

    chamados_para_atualizar_sla = chamados_base.exclude(
        status__in=["resolvido", "cancelado"]
    ).order_by(
        "-criado_em"
    )[:100]

    atualizar_sla_solicitacoes_dashboard(chamados_para_atualizar_sla)

    chamados_base = SolicitacaoTI.objects.filter(
        ativo=True
    )

    if modulo_origem:
        chamados_base = chamados_base.filter(
            modulo_origem=modulo_origem
        )

    chamados_base = filtrar_chamados_ti_dashboard(user, chamados_base)

    chamados_abertos_base = chamados_base.exclude(
        status__in=["resolvido", "cancelado"]
    )

    ultimos_chamados = chamados_base.select_related(
        "unidade",
        "setor",
        "solicitante",
        "responsavel_ti"
    ).order_by(
        "-criado_em"
    )[:limite]

    return {
        "total_chamados_ti": chamados_base.count(),
        "total_chamados_ti_abertos": chamados_base.filter(status="aberto").count(),
        "total_chamados_ti_atendimento": chamados_base.filter(status="em_atendimento").count(),
        "total_chamados_ti_aguardando": chamados_base.filter(
            Q(status="aguardando_usuario") |
            Q(status="aguardando_terceiro")
        ).count(),
        "total_chamados_ti_resolvidos": chamados_base.filter(status="resolvido").count(),
        "total_chamados_ti_sla_alerta": chamados_abertos_base.filter(
            sla_status="proximo_vencimento"
        ).count(),
        "total_chamados_ti_sla_estourado": chamados_abertos_base.filter(
            sla_status="estourado"
        ).count(),
        "total_chamados_ti_sem_responsavel": chamados_abertos_base.filter(
            responsavel_ti__isnull=True
        ).count(),
        "total_chamados_ti_criticos": chamados_abertos_base.filter(
            prioridade="critica"
        ).count(),
        "ultimos_chamados_ti": ultimos_chamados,
    }


def buscar_ocorrencias_ativas(user):
    unidade_usuario = obter_unidade_usuario(user)

    return OcorrenciaSistema.objects.filter(
        ativo=True
    ).filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True)
    ).select_related(
        "sistema",
        "unidade"
    ).order_by(
        "-atualizado_em"
    )[:5]


def montar_categorias_modulos(user):
    if usuario_eh_admin_ti(user):
        modulos = Modulo.objects.filter(ativo=True)
    else:
        grupos_usuario = user.groups.all()

        modulos = Modulo.objects.filter(
            ativo=True
        ).filter(
            Q(grupos_permitidos__in=grupos_usuario) |
            Q(grupos_permitidos__isnull=True)
        ).distinct()

    categorias = []

    for chave, nome in Modulo.CATEGORIA_CHOICES:
        itens = modulos.filter(
            categoria=chave
        ).order_by(
            "ordem",
            "nome"
        )

        if itens.exists():
            categorias.append({
                "chave": chave,
                "nome": nome,
                "modulos": itens,
            })

    return modulos, categorias


def montar_contexto_portal(user):
    modulos, categorias = montar_categorias_modulos(user)
    favoritos = listar_favoritos(user)

    ocorrencias_ativas = buscar_ocorrencias_ativas(user)
    avisos_dashboard = buscar_avisos_dashboard(user)
    documentos_dashboard = buscar_documentos_dashboard(user)
    links_rapidos = buscar_links_rapidos(user)
    ultimos_manuais = buscar_ultimos_manuais(user)

    pode_acessar_solicitacoes_ti = usuario_pode_acessar_solicitacoes_ti(user)
    pode_acessar_mv = usuario_pode_acessar_modulo_por_nome(
        user,
        "MV / Sistema Hospitalar",
    )
    pode_ver_painel_tecnico = usuario_eh_ti(user)
    impressoras_alerta = []
    if pode_ver_painel_tecnico:
        from inventario_ti.models import ImpressoraMonitorada
        queryset = ImpressoraMonitorada.objects.filter(ativo=True).select_related("unidade")
        if not user.is_superuser:
            queryset = queryset.filter(unidade=user.unidade)
        impressoras_alerta = [item for item in queryset.order_by("local") if item.possui_alerta]

    resumo_chamados_ti = {
        "total_chamados_ti": 0,
        "total_chamados_ti_abertos": 0,
        "total_chamados_ti_atendimento": 0,
        "total_chamados_ti_aguardando": 0,
        "total_chamados_ti_resolvidos": 0,
        "total_chamados_ti_sla_alerta": 0,
        "total_chamados_ti_sla_estourado": 0,
        "total_chamados_ti_sem_responsavel": 0,
        "total_chamados_ti_criticos": 0,
        "ultimos_chamados_ti": SolicitacaoTI.objects.none(),
    }

    if pode_acessar_solicitacoes_ti:
        resumo_chamados_ti = buscar_resumo_chamados_ti(user)

    resumo_inventario_ti = {
        "total_computadores": 0,
        "total_computadores_online": 0,
        "total_computadores_offline": 0,
        "total_computadores_sem_patrimonio": 0,
        "ultimos_computadores": [],
    }

    if pode_ver_painel_tecnico:
        resumo_inventario_ti = buscar_resumo_inventario_ti()

    timeline_global = montar_timeline_global(
        computadores=resumo_inventario_ti.get("ultimos_computadores", []),
        chamados_ti=resumo_chamados_ti.get("ultimos_chamados_ti", []),
        ocorrencias=ocorrencias_ativas,
        limite=10,
    )

    return {
        "page_title": "Portal",
        "categorias": categorias,
        "favoritos": favoritos,
        "favoritos_ids": [favorito.modulo_id for favorito in favoritos],
        "ocorrencias_ativas": ocorrencias_ativas,
        "avisos_dashboard": avisos_dashboard,
        "documentos_dashboard": documentos_dashboard,
        "links_rapidos": links_rapidos,
        "ultimos_manuais": ultimos_manuais,
        "total_modulos": modulos.count(),
        "total_ocorrencias": len(ocorrencias_ativas),
        "total_avisos": len(avisos_dashboard),
        "total_documentos_alerta": len(documentos_dashboard),
        "total_links": len(links_rapidos),
        "total_manuais": len(ultimos_manuais),
        "pode_ver_painel_tecnico": pode_ver_painel_tecnico,
        "pode_acessar_inventario_ti": pode_ver_painel_tecnico,
        "pode_acessar_solicitacoes_ti": pode_acessar_solicitacoes_ti,
        "pode_acessar_mv": pode_acessar_mv,
        "pode_acessar_administracao": usuario_eh_admin_ti(user),
        **resumo_chamados_ti,
        **resumo_inventario_ti,
        "timeline_global": timeline_global,
        "impressoras_alerta": impressoras_alerta,
    }
