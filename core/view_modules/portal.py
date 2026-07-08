from .common import *


@login_required(login_url='/')
def portal(request):
    user = request.user
    unidade_usuario = obter_unidade_usuario(user)

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
        itens = modulos.filter(categoria=chave).order_by('ordem', 'nome')

        if itens.exists():
            categorias.append({
                'chave': chave,
                'nome': nome,
                'modulos': itens,
            })

    ocorrencias_ativas = OcorrenciaSistema.objects.filter(
        ativo=True
    ).filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True)
    ).select_related(
        'sistema',
        'unidade'
    ).order_by(
        '-atualizado_em'
    )[:5]

    avisos_dashboard = buscar_avisos_dashboard(user)
    documentos_dashboard = buscar_documentos_dashboard(user)

    links_rapidos = ConteudoModulo.objects.none()
    ultimos_manuais = ConteudoModulo.objects.none()

    try:
        modulo_links = Modulo.objects.get(
            nome='Links Úteis / Sistemas Internos',
            ativo=True
        )

        if usuario_pode_acessar_modulo(user, modulo_links.nome):
            links_rapidos = buscar_conteudos_permitidos(
                user,
                modulo_links
            ).filter(
                tipo='link'
            ).select_related(
                'unidade'
            ).order_by(
                'ordem',
                'titulo'
            )[:6]

    except Modulo.DoesNotExist:
        pass

    try:
        modulo_manuais = Modulo.objects.get(
            nome='Manuais e Procedimentos',
            ativo=True
        )

        if usuario_pode_acessar_modulo(user, modulo_manuais.nome):
            ultimos_manuais = buscar_conteudos_permitidos(
                user,
                modulo_manuais
            ).select_related(
                'unidade'
            ).order_by(
                '-atualizado_em',
                'titulo'
            )[:5]

    except Modulo.DoesNotExist:
        pass


    pode_ver_painel_tecnico = usuario_pode_ver_painel_tecnico(user)
    pode_acessar_solicitacoes_ti = usuario_pode_acessar_solicitacoes_ti(user)
    pode_acessar_inventario_ti = usuario_pode_acessar_inventario_ti(user)

    resumo_chamados_ti = {
        'total_chamados_ti': 0,
        'total_chamados_ti_abertos': 0,
        'total_chamados_ti_atendimento': 0,
        'total_chamados_ti_aguardando': 0,
        'total_chamados_ti_resolvidos': 0,
        'total_chamados_ti_sla_alerta': 0,
        'total_chamados_ti_sla_estourado': 0,
        'total_chamados_ti_sem_responsavel': 0,
        'total_chamados_ti_criticos': 0,
        'ultimos_chamados_ti': SolicitacaoTI.objects.none(),
    }

    if pode_acessar_solicitacoes_ti:
        resumo_chamados_ti = buscar_resumo_chamados_ti(user)

    resumo_inventario_ti = {
        'total_computadores': 0,
        'total_computadores_online': 0,
        'total_computadores_offline': 0,
        'total_computadores_sem_patrimonio': 0,
        'ultimos_computadores': [],
    }

    if pode_acessar_inventario_ti:
        resumo_inventario_ti = buscar_resumo_inventario_ti()

    return render(request, 'core/portal.html', {
        'page_title': 'Portal',
        'categorias': categorias,
        'ocorrencias_ativas': ocorrencias_ativas,
        'avisos_dashboard': avisos_dashboard,
        'documentos_dashboard': documentos_dashboard,
        'links_rapidos': links_rapidos,
        'ultimos_manuais': ultimos_manuais,
        'total_modulos': modulos.count(),
        'total_ocorrencias': len(ocorrencias_ativas),
        'total_avisos': len(avisos_dashboard),
        'total_documentos_alerta': len(documentos_dashboard),
        'total_links': len(links_rapidos),
        'total_manuais': len(ultimos_manuais),
        'acessos_botoes_rapidos': montar_acessos_botoes_rapidos(user),
        'pode_ver_painel_tecnico': pode_ver_painel_tecnico,
        'pode_acessar_solicitacoes_ti': pode_acessar_solicitacoes_ti,
        'pode_acessar_inventario_ti': pode_acessar_inventario_ti,
        **resumo_chamados_ti,
        **resumo_inventario_ti,
        'pode_acessar_administracao': usuario_pode_acessar_administracao(user),
    })
