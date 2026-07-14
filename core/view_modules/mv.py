from .common import *
from django.db.models import Min, Subquery
from convenios.mv_oracle import IntegracaoMVErro, sincronizar_unidade
from convenios.models import SincronizacaoMVExecucao


@login_required(login_url='/')
def redirect_convenios_legacy(request):
    """Preserva atalhos antigos e direciona para a URL canonica do MV."""
    nome_modulo = 'MV / Sistema Hospitalar'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    return redirect('mv_convenios')


@login_required(login_url='/')
def modulo_mv(request):
    nome_modulo = 'MV / Sistema Hospitalar'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    conteudos = buscar_conteudos_permitidos(request.user, modulo)
    pode_gerenciar_mv = usuario_pode_gerenciar_mv(request.user)

    conteudos_por_tipo = {
        'manual': conteudos.filter(tipo='manual'),
        'convenio': conteudos.filter(tipo='convenio'),
        'contingencia': conteudos.filter(tipo='contingencia'),
        'link': conteudos.filter(tipo='link'),
        'chamado': conteudos.filter(tipo='chamado'),
        'observacao': conteudos.filter(tipo='observacao'),
    }

    total_convenios = Convenio.objects.count()
    total_convenios_ativos = Convenio.objects.filter(ativo=True).count()
    total_planos = PlanoConvenio.objects.count()
    total_regras_ativas = RegraAtendimentoConvenio.objects.filter(ativo=True).count()
    total_procedimentos_proibidos = ProcedimentoProibidoPlano.objects.filter(ativo=True).count()

    chamados_mv_base = SolicitacaoTI.objects.filter(
        ativo=True,
        modulo_origem='mv'
    )

    if not usuario_eh_admin_ti(request.user):
        chamados_mv_base = chamados_mv_base.filter(
            solicitante=request.user
        )

    chamados_mv = chamados_mv_base.select_related(
        'unidade',
        'setor',
        'solicitante',
        'responsavel_ti'
    ).order_by(
        '-criado_em'
    )[:8]

    total_chamados_mv_abertos = chamados_mv_base.exclude(
        status__in=['resolvido', 'cancelado']
    ).count()

    total_chamados_mv_atendimento = chamados_mv_base.filter(
        status='em_atendimento'
    ).count()

    total_chamados_mv_resolvidos = chamados_mv_base.filter(
        status='resolvido'
    ).count()

    return render(request, 'core/modulo_mv.html', {
        'page_title': 'MV / Sistema Hospitalar',
        'modulo': modulo,
        'conteudos_por_tipo': conteudos_por_tipo,
        'pode_gerenciar_mv': pode_gerenciar_mv,
        'chamados_mv': chamados_mv,
        'total_chamados_mv_abertos': total_chamados_mv_abertos,
        'total_chamados_mv_atendimento': total_chamados_mv_atendimento,
        'total_chamados_mv_resolvidos': total_chamados_mv_resolvidos,
        'total_convenios': total_convenios,
        'total_convenios_ativos': total_convenios_ativos,
        'total_planos': total_planos,
        'total_regras_ativas': total_regras_ativas,
        'total_procedimentos_proibidos': total_procedimentos_proibidos,
    })

@login_required(login_url='/')
def mv_manuais(request):
    nome_modulo = 'MV / Sistema Hospitalar'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudos = buscar_conteudos_permitidos(request.user, modulo).filter(
        tipo='manual'
    )

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()

    if busca:
        conteudos = conteudos.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca)
        )

    if unidade_id:
        if unidade_id == 'geral':
            conteudos = conteudos.filter(unidade__isnull=True)
        else:
            conteudos = conteudos.filter(unidade_id=unidade_id)

    unidades = Unidade.objects.filter(ativo=True).order_by('nome')

    return render(request, 'core/mv_manuais.html', {
        'modulo': modulo,
        'conteudos': conteudos,
        'unidades': unidades,
        'busca': busca,
        'unidade_id': unidade_id,
    })

@login_required(login_url='/')
def mv_convenios(request):
    nome_modulo = 'MV / Sistema Hospitalar'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    pode_gerenciar_mv = usuario_pode_gerenciar_mv(request.user)

    regras = RegraAtendimentoConvenio.objects.select_related(
        'unidade',
        'convenio',
        'plano',
        'especialidade',
    )

    proibicoes = ProcedimentoProibidoPlano.objects.select_related(
        'convenio',
        'plano',
    )

    if not pode_gerenciar_mv:
        regras = regras.filter(ativo=True)
        proibicoes = proibicoes.filter(ativo=True)

    busca = request.GET.get('busca', '').strip()
    unidade_ativa = getattr(request.user, 'unidade', None)
    unidade_id = str(unidade_ativa.id) if unidade_ativa else ''
    if unidade_ativa:
        proibicoes = proibicoes.filter(unidade=unidade_ativa)
    else:
        proibicoes = proibicoes.none()
    convenio_id = request.GET.get('convenio', '').strip()
    plano_id = request.GET.get('plano', '').strip()
    tipo_atendimento = request.GET.get('tipo_atendimento', '').strip()
    especialidade_id = request.GET.get('especialidade', '').strip()
    status = request.GET.get('status', '').strip()
    procedimento = request.GET.get('procedimento', '').strip()
    consulta_realizada = any((
        busca,
        convenio_id,
        plano_id,
        tipo_atendimento,
        especialidade_id,
        status,
        procedimento,
    ))

    if busca:
        regras = regras.filter(
            Q(convenio__nome__icontains=busca) |
            Q(convenio__codigo_mv__icontains=busca) |
            Q(plano__nome__icontains=busca) |
            Q(plano__codigo_mv__icontains=busca) |
            Q(especialidade__nome__icontains=busca) |
            Q(observacao__icontains=busca)
        )

    if unidade_id:
        regras = regras.filter(unidade_id=unidade_id)

    if convenio_id:
        regras = regras.filter(convenio_id=convenio_id)
        proibicoes = proibicoes.filter(convenio_id=convenio_id)

    if plano_id:
        regras = regras.filter(plano_id=plano_id)
        proibicoes = proibicoes.filter(plano_id=plano_id)

    if tipo_atendimento:
        regras = regras.filter(tipo_atendimento=tipo_atendimento)

    if especialidade_id:
        regras = regras.filter(especialidade_id=especialidade_id)

    if status:
        regras = regras.filter(status=status)
        # O status pertence às regras de atendimento. Ao selecionar um
        # status, não misture o resultado com o relatório independente de
        # procedimentos proibidos.
        proibicoes = proibicoes.none()

    if procedimento:
        proibicoes = proibicoes.filter(
            Q(codigo_procedimento__icontains=procedimento) |
            Q(descricao_procedimento__icontains=procedimento)
        )
    else:
        proibicoes = proibicoes.none()

    # Importações e cadastros antigos podem conter a mesma regra mais de uma
    # vez. Mantemos um único registro por combinação funcional, sem esconder
    # regras diferentes do mesmo convênio ou plano.
    ids_regras_unicas = regras.values(
        'unidade_id',
        'convenio_id',
        'plano_id',
        'tipo_atendimento',
        'especialidade_id',
        'status',
        'exige_autorizacao',
        'observacao',
        'ativo',
    ).annotate(
        primeiro_id=Min('id'),
    ).values('primeiro_id')
    regras = RegraAtendimentoConvenio.objects.filter(
        pk__in=Subquery(ids_regras_unicas),
    ).select_related('unidade', 'convenio', 'plano', 'especialidade')

    if not consulta_realizada:
        regras = regras.none()
        proibicoes = proibicoes.none()

    regras = regras.order_by(
        'unidade__nome',
        'convenio__nome',
        'plano__nome',
        'tipo_atendimento',
        'especialidade__nome',
    )

    proibicoes = proibicoes.distinct().order_by(
        'convenio__nome',
        'plano__nome',
        'descricao_procedimento',
    )


    resumo_chamados_mv = buscar_resumo_chamados_ti(
        request.user,
        limite=8,
        modulo_origem='mv'
    )

    chamados_mv = resumo_chamados_mv['ultimos_chamados_ti']
    total_chamados_mv_abertos = (
        resumo_chamados_mv['total_chamados_ti_abertos'] +
        resumo_chamados_mv['total_chamados_ti_atendimento'] +
        resumo_chamados_mv['total_chamados_ti_aguardando']
    )
    total_chamados_mv_atendimento = resumo_chamados_mv['total_chamados_ti_atendimento']
    total_chamados_mv_resolvidos = resumo_chamados_mv['total_chamados_ti_resolvidos']
    if unidade_ativa:
        total_convenios_unidade = Convenio.objects.filter(
            unidades=unidade_ativa,
        ).distinct().count()
        total_planos_unidade = PlanoConvenio.objects.filter(
            convenio__unidades=unidade_ativa,
        ).distinct().count()
        total_regras_unidade = RegraAtendimentoConvenio.objects.filter(
            unidade=unidade_ativa,
        ).count()
        total_procedimentos_unidade = ProcedimentoProibidoPlano.objects.filter(
            unidade=unidade_ativa,
        ).distinct().count()
    else:
        total_convenios_unidade = 0
        total_planos_unidade = 0
        total_regras_unidade = 0
        total_procedimentos_unidade = 0
    ultima_sincronizacao_mv = (
        SincronizacaoMVExecucao.objects.filter(unidade=unidade_ativa).first()
        if unidade_ativa else None
    )

    return render(request, 'core/mv_convenios.html', {
        'regras': regras,
        'proibicoes': proibicoes,
        'unidades': Unidade.objects.filter(ativo=True).order_by('nome'),
        'convenios': Convenio.objects.filter(ativo=True, unidades=unidade_ativa).distinct().order_by('nome') if unidade_ativa else Convenio.objects.none(),
        'planos': PlanoConvenio.objects.filter(ativo=True, convenio__unidades=unidade_ativa).distinct().select_related('convenio').order_by('convenio__nome', 'nome') if unidade_ativa else PlanoConvenio.objects.none(),
        'especialidades': Especialidade.objects.filter(ativo=True).order_by('nome'),
        'todos_convenios': Convenio.objects.all().order_by('nome'),
        'todos_planos': PlanoConvenio.objects.select_related('convenio').all().order_by('convenio__nome', 'nome'),
        'todas_especialidades': Especialidade.objects.all().order_by('nome'),
        'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
        'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
        'busca': busca,
        'unidade_id': unidade_id,
        'convenio_id': convenio_id,
        'plano_id': plano_id,
        'tipo_atendimento': tipo_atendimento,
        'especialidade_id': especialidade_id,
        'status': status,
        'procedimento': procedimento,
        'consulta_realizada': consulta_realizada,
        'pode_gerenciar_mv': pode_gerenciar_mv,
        'unidade_ativa': unidade_ativa,
        'chamados_mv': chamados_mv,
        'total_chamados_mv_abertos': total_chamados_mv_abertos,
        'total_chamados_mv_atendimento': total_chamados_mv_atendimento,
        'total_chamados_mv_resolvidos': total_chamados_mv_resolvidos,
        'total_convenios': total_convenios_unidade,
        'total_planos': total_planos_unidade,
        'total_especialidades': Especialidade.objects.count(),
        'total_regras': total_regras_unidade,
        'total_procedimentos': total_procedimentos_unidade,
        'ultima_sincronizacao_mv': ultima_sincronizacao_mv,
    })


@login_required(login_url='/')
@require_POST
def sincronizar_convenios_mv(request):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    unidade = getattr(request.user, 'unidade', None)
    if unidade is None:
        messages.error(request, 'Selecione uma empresa antes de sincronizar.')
        return redirect('mv_convenios')

    try:
        execucao = SincronizacaoMVExecucao.objects.create(unidade=unidade)
        resultado = sincronizar_unidade(unidade)
    except IntegracaoMVErro as exc:
        execucao.status = 'erro'
        execucao.mensagem = str(exc)[:4000]
        execucao.finalizado_em = timezone.now()
        execucao.save(update_fields=['status', 'mensagem', 'finalizado_em'])
        messages.error(request, str(exc))
    else:
        execucao.status = 'sucesso'
        execucao.convenios = resultado['convenios']
        execucao.planos = resultado['planos']
        execucao.regras = resultado['regras']
        execucao.procedimentos = resultado['procedimentos']
        execucao.finalizado_em = timezone.now()
        execucao.save(update_fields=[
            'status', 'convenios', 'planos', 'regras', 'procedimentos', 'finalizado_em',
        ])
        messages.success(
            request,
            f'MV sincronizado para {unidade.sigla}: '
            f'{resultado["convenios"]} convênios, {resultado["planos"]} planos e '
            f'{resultado["regras"]} regras, '
            f'{resultado["procedimentos"]} procedimentos proibidos.',
        )
        RegistroAuditoria.objects.create(
            modulo='convenios',
            acao='atualizado',
            titulo=f'Convênios sincronizados com MV - {unidade.sigla}',
            descricao=str(resultado),
            modelo='Convenio',
            usuario=request.user,
            unidade=unidade,
            ip_origem=obter_ip_cliente(request),
        )
    return redirect('mv_convenios')

@login_required(login_url='/')
def novo_convenio_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'codigo_mv': '',
        'nome': '',
        'tipo_mv': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_convenio(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do convênio.')

        if Convenio.objects.filter(nome__iexact=form_data['nome']).exists():
            erros.append('Já existe um convênio com este nome.')

        if form_data['codigo_mv'] and Convenio.objects.filter(codigo_mv=form_data['codigo_mv']).exists():
            erros.append('Já existe um convênio com este código MV.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_convenio_mv.html', {
                'titulo': 'Novo convênio MV',
                'subtitulo': 'Cadastre um convênio utilizado no MV.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/convenios/novo/',
                'modo': 'novo',
            })

        convenio = Convenio.objects.create(
            codigo_mv=form_data['codigo_mv'],
            nome=form_data['nome'],
            tipo_mv=form_data['tipo_mv'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_convenio_mv(
            request,
            convenio,
            'criado',
            f'Convênio MV criado: {convenio.nome}'
        )

        messages.success(request, 'Convênio cadastrado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_convenio_mv.html', {
        'titulo': 'Novo convênio MV',
        'subtitulo': 'Cadastre um convênio utilizado no MV.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/convenios/novo/',
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_convenio_mv(request, convenio_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    convenio = get_object_or_404(Convenio, id=convenio_id)
    form_data = convenio_para_form_data(convenio)

    if request.method == 'POST':
        form_data = montar_form_data_convenio(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do convênio.')

        if Convenio.objects.filter(nome__iexact=form_data['nome']).exclude(id=convenio.id).exists():
            erros.append('Já existe outro convênio com este nome.')

        if form_data['codigo_mv'] and Convenio.objects.filter(codigo_mv=form_data['codigo_mv']).exclude(id=convenio.id).exists():
            erros.append('Já existe outro convênio com este código MV.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_convenio_mv.html', {
                'titulo': 'Editar convênio MV',
                'subtitulo': 'Atualize os dados do convênio.',
                'form_data': form_data,
                'convenio_editado': convenio,
                'url_salvar': f'/portal/modulos/mv/convenios/editar/{convenio.id}/',
                'modo': 'editar',
            })

        convenio.codigo_mv = form_data['codigo_mv']
        convenio.nome = form_data['nome']
        convenio.tipo_mv = form_data['tipo_mv']
        convenio.ativo = form_data['ativo']
        convenio.save()

        registrar_auditoria_convenio_mv(
            request,
            convenio,
            'alterado',
            f'Convênio MV alterado: {convenio.nome}'
        )

        messages.success(request, 'Convênio atualizado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_convenio_mv.html', {
        'titulo': 'Editar convênio MV',
        'subtitulo': 'Atualize os dados do convênio.',
        'form_data': form_data,
        'convenio_editado': convenio,
        'url_salvar': f'/portal/modulos/mv/convenios/editar/{convenio.id}/',
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_convenio_mv(request, convenio_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    convenio = get_object_or_404(Convenio, id=convenio_id)
    convenio.ativo = False
    convenio.save()

    registrar_auditoria_convenio_mv(request, convenio, 'alterado', f'Convênio MV inativado: {convenio.nome}')
    messages.success(request, 'Convênio inativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def reativar_convenio_mv(request, convenio_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    convenio = get_object_or_404(Convenio, id=convenio_id)
    convenio.ativo = True
    convenio.save()

    registrar_auditoria_convenio_mv(request, convenio, 'alterado', f'Convênio MV reativado: {convenio.nome}')
    messages.success(request, 'Convênio reativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def novo_plano_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    dados = buscar_dados_formularios_mv()

    form_data = {
        'convenio': '',
        'codigo_mv': '',
        'nome': '',
        'regra_codigo_mv': '',
        'regra_nome_mv': '',
        'indice_codigo_mv': '',
        'indice_nome_mv': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_plano(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['nome']:
            erros.append('Informe o nome do plano.')

        if form_data['convenio'] and form_data['codigo_mv']:
            if PlanoConvenio.objects.filter(convenio_id=form_data['convenio'], codigo_mv=form_data['codigo_mv']).exists():
                erros.append('Já existe um plano com este código MV para o convênio selecionado.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_plano_mv.html', {
                'titulo': 'Novo plano MV',
                'subtitulo': 'Cadastre um plano vinculado ao convênio.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/planos/novo/',
                **dados,
                'modo': 'novo',
            })

        plano = PlanoConvenio.objects.create(
            convenio_id=form_data['convenio'],
            codigo_mv=form_data['codigo_mv'],
            nome=form_data['nome'],
            regra_codigo_mv=form_data['regra_codigo_mv'],
            regra_nome_mv=form_data['regra_nome_mv'],
            indice_codigo_mv=form_data['indice_codigo_mv'],
            indice_nome_mv=form_data['indice_nome_mv'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_plano_mv(request, plano, 'criado', f'Plano MV criado: {plano.nome}')
        messages.success(request, 'Plano cadastrado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_plano_mv.html', {
        'titulo': 'Novo plano MV',
        'subtitulo': 'Cadastre um plano vinculado ao convênio.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/planos/novo/',
        **dados,
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_plano_mv(request, plano_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    plano = get_object_or_404(PlanoConvenio.objects.select_related('convenio'), id=plano_id)
    dados = buscar_dados_formularios_mv()
    form_data = plano_para_form_data(plano)

    if request.method == 'POST':
        form_data = montar_form_data_plano(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['nome']:
            erros.append('Informe o nome do plano.')

        if form_data['convenio'] and form_data['codigo_mv']:
            if PlanoConvenio.objects.filter(
                convenio_id=form_data['convenio'],
                codigo_mv=form_data['codigo_mv']
            ).exclude(id=plano.id).exists():
                erros.append('Já existe outro plano com este código MV para o convênio selecionado.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_plano_mv.html', {
                'titulo': 'Editar plano MV',
                'subtitulo': 'Atualize os dados do plano.',
                'form_data': form_data,
                'plano_editado': plano,
                'url_salvar': f'/portal/modulos/mv/planos/editar/{plano.id}/',
                **dados,
                'modo': 'editar',
            })

        plano.convenio_id = form_data['convenio']
        plano.codigo_mv = form_data['codigo_mv']
        plano.nome = form_data['nome']
        plano.regra_codigo_mv = form_data['regra_codigo_mv']
        plano.regra_nome_mv = form_data['regra_nome_mv']
        plano.indice_codigo_mv = form_data['indice_codigo_mv']
        plano.indice_nome_mv = form_data['indice_nome_mv']
        plano.ativo = form_data['ativo']
        plano.save()

        registrar_auditoria_plano_mv(request, plano, 'alterado', f'Plano MV alterado: {plano.nome}')
        messages.success(request, 'Plano atualizado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_plano_mv.html', {
        'titulo': 'Editar plano MV',
        'subtitulo': 'Atualize os dados do plano.',
        'form_data': form_data,
        'plano_editado': plano,
        'url_salvar': f'/portal/modulos/mv/planos/editar/{plano.id}/',
        **dados,
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_plano_mv(request, plano_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    plano = get_object_or_404(PlanoConvenio.objects.select_related('convenio'), id=plano_id)
    plano.ativo = False
    plano.save()

    registrar_auditoria_plano_mv(request, plano, 'alterado', f'Plano MV inativado: {plano.nome}')
    messages.success(request, 'Plano inativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def reativar_plano_mv(request, plano_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    plano = get_object_or_404(PlanoConvenio.objects.select_related('convenio'), id=plano_id)
    plano.ativo = True
    plano.save()

    registrar_auditoria_plano_mv(request, plano, 'alterado', f'Plano MV reativado: {plano.nome}')
    messages.success(request, 'Plano reativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def nova_especialidade_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'nome': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_especialidade(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome da especialidade.')

        if Especialidade.objects.filter(nome__iexact=form_data['nome']).exists():
            erros.append('Já existe uma especialidade com este nome.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_especialidade_mv.html', {
                'titulo': 'Nova especialidade MV',
                'subtitulo': 'Cadastre uma especialidade para uso nas regras de convênio.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/especialidades/nova/',
                'modo': 'novo',
            })

        especialidade = Especialidade.objects.create(
            nome=form_data['nome'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_especialidade_mv(request, especialidade, 'criado', f'Especialidade MV criada: {especialidade.nome}')
        messages.success(request, 'Especialidade cadastrada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_especialidade_mv.html', {
        'titulo': 'Nova especialidade MV',
        'subtitulo': 'Cadastre uma especialidade para uso nas regras de convênio.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/especialidades/nova/',
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_especialidade_mv(request, especialidade_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    especialidade = get_object_or_404(Especialidade, id=especialidade_id)
    form_data = especialidade_para_form_data(especialidade)

    if request.method == 'POST':
        form_data = montar_form_data_especialidade(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome da especialidade.')

        if Especialidade.objects.filter(nome__iexact=form_data['nome']).exclude(id=especialidade.id).exists():
            erros.append('Já existe outra especialidade com este nome.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_especialidade_mv.html', {
                'titulo': 'Editar especialidade MV',
                'subtitulo': 'Atualize os dados da especialidade.',
                'form_data': form_data,
                'especialidade_editada': especialidade,
                'url_salvar': f'/portal/modulos/mv/especialidades/editar/{especialidade.id}/',
                'modo': 'editar',
            })

        especialidade.nome = form_data['nome']
        especialidade.ativo = form_data['ativo']
        especialidade.save()

        registrar_auditoria_especialidade_mv(request, especialidade, 'alterado', f'Especialidade MV alterada: {especialidade.nome}')
        messages.success(request, 'Especialidade atualizada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_especialidade_mv.html', {
        'titulo': 'Editar especialidade MV',
        'subtitulo': 'Atualize os dados da especialidade.',
        'form_data': form_data,
        'especialidade_editada': especialidade,
        'url_salvar': f'/portal/modulos/mv/especialidades/editar/{especialidade.id}/',
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_especialidade_mv(request, especialidade_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    especialidade = get_object_or_404(Especialidade, id=especialidade_id)
    especialidade.ativo = False
    especialidade.save()

    registrar_auditoria_especialidade_mv(request, especialidade, 'alterado', f'Especialidade MV inativada: {especialidade.nome}')
    messages.success(request, 'Especialidade inativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def reativar_especialidade_mv(request, especialidade_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    especialidade = get_object_or_404(Especialidade, id=especialidade_id)
    especialidade.ativo = True
    especialidade.save()

    registrar_auditoria_especialidade_mv(request, especialidade, 'alterado', f'Especialidade MV reativada: {especialidade.nome}')
    messages.success(request, 'Especialidade reativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def nova_regra_convenio_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    dados = buscar_dados_formularios_mv()

    form_data = {
        'unidade': '',
        'convenio': '',
        'plano': '',
        'tipo_atendimento': 'consulta',
        'especialidade': '',
        'status': 'aceito',
        'exige_autorizacao': False,
        'observacao': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_regra(request)
        erros = []

        if not form_data['unidade']:
            erros.append('Informe a unidade.')

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['tipo_atendimento']:
            erros.append('Informe o tipo de atendimento.')

        if not form_data['status']:
            erros.append('Informe o status da regra.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_regra_convenio_mv.html', {
                'titulo': 'Nova regra de convênio',
                'subtitulo': 'Cadastre uma regra manual de atendimento.',
                'form_data': form_data,
                'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
                'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
                'url_salvar': '/portal/modulos/mv/regras/nova/',
                **dados,
                'modo': 'novo',
            })

        regra = RegraAtendimentoConvenio.objects.create(
            unidade_id=form_data['unidade'],
            convenio_id=form_data['convenio'],
            plano_id=form_data['plano'],
            tipo_atendimento=form_data['tipo_atendimento'],
            especialidade_id=form_data['especialidade'] or None,
            status=form_data['status'],
            exige_autorizacao=form_data['exige_autorizacao'],
            observacao=form_data['observacao'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_regra_mv(request, regra, 'criado', f'Regra de convênio criada: {regra}')
        messages.success(request, 'Regra cadastrada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_regra_convenio_mv.html', {
        'titulo': 'Nova regra de convênio',
        'subtitulo': 'Cadastre uma regra manual de atendimento.',
        'form_data': form_data,
        'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
        'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
        'url_salvar': '/portal/modulos/mv/regras/nova/',
        **dados,
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_regra_convenio_mv(request, regra_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    regra = get_object_or_404(
        RegraAtendimentoConvenio.objects.select_related('unidade', 'convenio', 'plano', 'especialidade'),
        id=regra_id
    )

    dados = buscar_dados_formularios_mv()
    form_data = regra_para_form_data(regra)

    if request.method == 'POST':
        form_data = montar_form_data_regra(request)
        erros = []

        if not form_data['unidade']:
            erros.append('Informe a unidade.')

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['tipo_atendimento']:
            erros.append('Informe o tipo de atendimento.')

        if not form_data['status']:
            erros.append('Informe o status da regra.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_regra_convenio_mv.html', {
                'titulo': 'Editar regra de convênio',
                'subtitulo': 'Atualize a regra manual de atendimento.',
                'form_data': form_data,
                'regra_editada': regra,
                'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
                'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
                'url_salvar': f'/portal/modulos/mv/regras/editar/{regra.id}/',
                **dados,
                'modo': 'editar',
            })

        regra.unidade_id = form_data['unidade']
        regra.convenio_id = form_data['convenio']
        regra.plano_id = form_data['plano']
        regra.tipo_atendimento = form_data['tipo_atendimento']
        regra.especialidade_id = form_data['especialidade'] or None
        regra.status = form_data['status']
        regra.exige_autorizacao = form_data['exige_autorizacao']
        regra.observacao = form_data['observacao']
        regra.ativo = form_data['ativo']
        regra.save()

        registrar_auditoria_regra_mv(request, regra, 'alterado', f'Regra de convênio alterada: {regra}')
        messages.success(request, 'Regra atualizada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_regra_convenio_mv.html', {
        'titulo': 'Editar regra de convênio',
        'subtitulo': 'Atualize a regra manual de atendimento.',
        'form_data': form_data,
        'regra_editada': regra,
        'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
        'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
        'url_salvar': f'/portal/modulos/mv/regras/editar/{regra.id}/',
        **dados,
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_regra_convenio_mv(request, regra_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    regra = get_object_or_404(RegraAtendimentoConvenio, id=regra_id)
    regra.ativo = False
    regra.save()

    registrar_auditoria_regra_mv(request, regra, 'alterado', f'Regra de convênio inativada: {regra}')
    messages.success(request, 'Regra inativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def reativar_regra_convenio_mv(request, regra_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    regra = get_object_or_404(RegraAtendimentoConvenio, id=regra_id)
    regra.ativo = True
    regra.save()

    registrar_auditoria_regra_mv(request, regra, 'alterado', f'Regra de convênio reativada: {regra}')
    messages.success(request, 'Regra reativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def novo_procedimento_proibido_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    dados = buscar_dados_formularios_mv()

    form_data = {
        'convenio': '',
        'plano': '',
        'codigo_procedimento': '',
        'descricao_procedimento': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_procedimento(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['codigo_procedimento']:
            erros.append('Informe o código do procedimento.')

        if not form_data['descricao_procedimento']:
            erros.append('Informe a descrição do procedimento.')

        if form_data['plano'] and form_data['codigo_procedimento']:
            if ProcedimentoProibidoPlano.objects.filter(
                plano_id=form_data['plano'],
                codigo_procedimento=form_data['codigo_procedimento']
            ).exists():
                erros.append('Este procedimento já está cadastrado como proibido para este plano.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_procedimento_proibido_mv.html', {
                'titulo': 'Novo procedimento proibido',
                'subtitulo': 'Cadastre um procedimento proibido por plano.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/procedimentos-proibidos/novo/',
                **dados,
                'modo': 'novo',
            })

        procedimento = ProcedimentoProibidoPlano.objects.create(
            convenio_id=form_data['convenio'],
            plano_id=form_data['plano'],
            codigo_procedimento=form_data['codigo_procedimento'],
            descricao_procedimento=form_data['descricao_procedimento'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_procedimento_mv(
            request,
            procedimento,
            'criado',
            f'Procedimento proibido criado: {procedimento.codigo_procedimento}'
        )

        messages.success(request, 'Procedimento proibido cadastrado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_procedimento_proibido_mv.html', {
        'titulo': 'Novo procedimento proibido',
        'subtitulo': 'Cadastre um procedimento proibido por plano.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/procedimentos-proibidos/novo/',
        **dados,
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_procedimento_proibido_mv(request, procedimento_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    procedimento = get_object_or_404(
        ProcedimentoProibidoPlano.objects.select_related('convenio', 'plano'),
        id=procedimento_id
    )

    dados = buscar_dados_formularios_mv()
    form_data = procedimento_para_form_data(procedimento)

    if request.method == 'POST':
        form_data = montar_form_data_procedimento(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['codigo_procedimento']:
            erros.append('Informe o código do procedimento.')

        if not form_data['descricao_procedimento']:
            erros.append('Informe a descrição do procedimento.')

        if form_data['plano'] and form_data['codigo_procedimento']:
            if ProcedimentoProibidoPlano.objects.filter(
                plano_id=form_data['plano'],
                codigo_procedimento=form_data['codigo_procedimento']
            ).exclude(id=procedimento.id).exists():
                erros.append('Outro procedimento com este código já está cadastrado como proibido para este plano.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_procedimento_proibido_mv.html', {
                'titulo': 'Editar procedimento proibido',
                'subtitulo': 'Atualize o procedimento proibido.',
                'form_data': form_data,
                'procedimento_editado': procedimento,
                'url_salvar': f'/portal/modulos/mv/procedimentos-proibidos/editar/{procedimento.id}/',
                **dados,
                'modo': 'editar',
            })

        procedimento.convenio_id = form_data['convenio']
        procedimento.plano_id = form_data['plano']
        procedimento.codigo_procedimento = form_data['codigo_procedimento']
        procedimento.descricao_procedimento = form_data['descricao_procedimento']
        procedimento.ativo = form_data['ativo']
        procedimento.save()

        registrar_auditoria_procedimento_mv(
            request,
            procedimento,
            'alterado',
            f'Procedimento proibido alterado: {procedimento.codigo_procedimento}'
        )

        messages.success(request, 'Procedimento proibido atualizado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_procedimento_proibido_mv.html', {
        'titulo': 'Editar procedimento proibido',
        'subtitulo': 'Atualize o procedimento proibido.',
        'form_data': form_data,
        'procedimento_editado': procedimento,
        'url_salvar': f'/portal/modulos/mv/procedimentos-proibidos/editar/{procedimento.id}/',
        **dados,
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_procedimento_proibido_mv(request, procedimento_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    procedimento = get_object_or_404(
        ProcedimentoProibidoPlano.objects.select_related('convenio', 'plano'),
        id=procedimento_id
    )

    procedimento.ativo = False
    procedimento.save()

    registrar_auditoria_procedimento_mv(
        request,
        procedimento,
        'alterado',
        f'Procedimento proibido inativado: {procedimento.codigo_procedimento}'
    )

    messages.success(request, 'Procedimento proibido inativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')

@login_required(login_url='/')
def reativar_procedimento_proibido_mv(request, procedimento_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    procedimento = get_object_or_404(
        ProcedimentoProibidoPlano.objects.select_related('convenio', 'plano'),
        id=procedimento_id
    )

    procedimento.ativo = True
    procedimento.save()

    registrar_auditoria_procedimento_mv(
        request,
        procedimento,
        'alterado',
        f'Procedimento proibido reativado: {procedimento.codigo_procedimento}'
    )

    messages.success(request, 'Procedimento proibido reativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')
