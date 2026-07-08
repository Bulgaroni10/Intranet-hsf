from .common import *


@login_required(login_url='/')
def status_sistemas(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    pode_gerenciar = usuario_pode_gerenciar_status(request.user)
    unidade_usuario = obter_unidade_usuario(request.user)

    ocorrencias_visiveis = OcorrenciaSistema.objects.filter(
        ativo=True
    ).filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True)
    ).select_related(
        'sistema',
        'unidade'
    ).order_by(
        '-atualizado_em'
    )

    if pode_gerenciar:
        sistemas = SistemaMonitorado.objects.all()
    else:
        sistemas = SistemaMonitorado.objects.filter(ativo=True)

    sistemas = sistemas.prefetch_related(
        Prefetch(
            'ocorrencias',
            queryset=ocorrencias_visiveis,
            to_attr='ocorrencias_visiveis'
        )
    ).order_by(
        'ordem',
        'nome'
    )

    resumo = {
        'operacional': 0,
        'instavel': 0,
        'indisponivel': 0,
        'manutencao': 0,
    }

    for sistema in sistemas:
        if sistema.ocorrencias_visiveis:
            status_atual = sistema.ocorrencias_visiveis[0].status
        else:
            status_atual = 'operacional'

        sistema.status_atual = status_atual

        if status_atual in resumo:
            resumo[status_atual] += 1
        else:
            resumo['operacional'] += 1

    return render(request, 'core/status_sistemas.html', {
        'page_title': 'Status dos Sistemas',
        'sistemas': sistemas,
        'ocorrencias_ativas': ocorrencias_visiveis,
        'resumo': resumo,
        'pode_gerenciar_status': pode_gerenciar,
        'total_sistemas': sistemas.count(),
        'total_sistemas_ativos': sistemas.filter(ativo=True).count(),
        'total_sistemas_inativos': sistemas.filter(ativo=False).count() if pode_gerenciar else 0,
    })

@login_required(login_url='/')
def novo_sistema_monitorado(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'nome': '',
        'descricao': '',
        'categoria': 'infraestrutura',
        'icone': '🖥️',
        'ordem': 0,
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_sistema(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do sistema.')

        if not form_data['categoria']:
            erros.append('Informe a categoria.')

        if SistemaMonitorado.objects.filter(nome__iexact=form_data['nome']).exists():
            erros.append('Já existe um sistema cadastrado com este nome.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_sistema_monitorado.html', {
                'titulo': 'Novo sistema monitorado',
                'subtitulo': 'Cadastre um sistema, serviço, link, servidor ou fornecedor monitorado pela TI.',
                'form_data': form_data,
                'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
                'url_salvar': '/portal/modulos/status-sistemas/sistema/novo/',
                'modo': 'novo',
            })

        sistema = SistemaMonitorado.objects.create(
            nome=form_data['nome'],
            descricao=form_data['descricao'],
            categoria=form_data['categoria'],
            icone=form_data['icone'],
            ordem=ordem,
            ativo=form_data['ativo'],
        )

        registrar_auditoria_sistema(
            request=request,
            sistema=sistema,
            acao='criado',
            titulo=f'Sistema monitorado criado: {sistema.nome}'
        )

        messages.success(request, 'Sistema monitorado cadastrado com sucesso.')
        return redirect('/portal/modulos/status-sistemas/')

    return render(request, 'core/formulario_sistema_monitorado.html', {
        'titulo': 'Novo sistema monitorado',
        'subtitulo': 'Cadastre um sistema, serviço, link, servidor ou fornecedor monitorado pela TI.',
        'form_data': form_data,
        'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
        'url_salvar': '/portal/modulos/status-sistemas/sistema/novo/',
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_sistema_monitorado(request, sistema_id):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistema = get_object_or_404(SistemaMonitorado, id=sistema_id)
    form_data = sistema_para_form_data(sistema)

    if request.method == 'POST':
        form_data = montar_form_data_sistema(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do sistema.')

        if not form_data['categoria']:
            erros.append('Informe a categoria.')

        if SistemaMonitorado.objects.filter(nome__iexact=form_data['nome']).exclude(id=sistema.id).exists():
            erros.append('Já existe outro sistema cadastrado com este nome.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_sistema_monitorado.html', {
                'titulo': 'Editar sistema monitorado',
                'subtitulo': 'Atualize o sistema selecionado.',
                'form_data': form_data,
                'sistema_editado': sistema,
                'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
                'url_salvar': f'/portal/modulos/status-sistemas/sistema/editar/{sistema.id}/',
                'modo': 'editar',
            })

        sistema.nome = form_data['nome']
        sistema.descricao = form_data['descricao']
        sistema.categoria = form_data['categoria']
        sistema.icone = form_data['icone']
        sistema.ordem = ordem
        sistema.ativo = form_data['ativo']
        sistema.save()

        registrar_auditoria_sistema(
            request=request,
            sistema=sistema,
            acao='alterado',
            titulo=f'Sistema monitorado alterado: {sistema.nome}'
        )

        messages.success(request, 'Sistema monitorado atualizado com sucesso.')
        return redirect('/portal/modulos/status-sistemas/')

    return render(request, 'core/formulario_sistema_monitorado.html', {
        'titulo': 'Editar sistema monitorado',
        'subtitulo': 'Atualize o sistema selecionado.',
        'form_data': form_data,
        'sistema_editado': sistema,
        'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
        'url_salvar': f'/portal/modulos/status-sistemas/sistema/editar/{sistema.id}/',
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_sistema_monitorado(request, sistema_id):
    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistema = get_object_or_404(SistemaMonitorado, id=sistema_id)
    sistema.ativo = False
    sistema.save()

    registrar_auditoria_sistema(
        request=request,
        sistema=sistema,
        acao='alterado',
        titulo=f'Sistema monitorado inativado: {sistema.nome}'
    )

    messages.success(request, 'Sistema monitorado inativado com sucesso.')
    return redirect('/portal/modulos/status-sistemas/')

@login_required(login_url='/')
def reativar_sistema_monitorado(request, sistema_id):
    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistema = get_object_or_404(SistemaMonitorado, id=sistema_id)
    sistema.ativo = True
    sistema.save()

    registrar_auditoria_sistema(
        request=request,
        sistema=sistema,
        acao='alterado',
        titulo=f'Sistema monitorado reativado: {sistema.nome}'
    )

    messages.success(request, 'Sistema monitorado reativado com sucesso.')
    return redirect('/portal/modulos/status-sistemas/')

@login_required(login_url='/')
def historico_ocorrencias_status(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    ocorrencias_filtradas = filtrar_ocorrencias_historico(request, request.user)

    sistemas = SistemaMonitorado.objects.filter(
        ativo=True
    ).order_by(
        'ordem',
        'nome'
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    total_ocorrencias = ocorrencias_filtradas.count()
    ocorrencias = ocorrencias_filtradas[:300]

    return render(request, 'core/historico_ocorrencias_status.html', {
        'page_title': 'Histórico de ocorrências',
        'ocorrencias': ocorrencias,
        'sistemas': sistemas,
        'unidades': unidades,
        'status_choices': OcorrenciaSistema.STATUS_CHOICES,
        'impacto_choices': OcorrenciaSistema.IMPACTO_CHOICES,
        'busca': request.GET.get('busca', '').strip(),
        'sistema_id': request.GET.get('sistema', '').strip(),
        'unidade_id': request.GET.get('unidade', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'impacto': request.GET.get('impacto', '').strip(),
        'data_inicio': request.GET.get('data_inicio', '').strip(),
        'data_fim': request.GET.get('data_fim', '').strip(),
        'total_ocorrencias': total_ocorrencias,
        'query_string': request.GET.urlencode(),
    })

@login_required(login_url='/')
def exportar_historico_ocorrencias_csv(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    ocorrencias = filtrar_ocorrencias_historico(request, request.user)

    nome_arquivo = f'historico_ocorrencias_{timezone.localdate().strftime("%Y%m%d")}.csv'

    response = HttpResponse(
        content_type='text/csv; charset=utf-8-sig'
    )
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'

    response.write('\ufeff')

    writer = csv.writer(
        response,
        delimiter=';',
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )

    writer.writerow([
        'ID',
        'Sistema',
        'Unidade',
        'Status',
        'Impacto',
        'Titulo',
        'Mensagem inicial',
        'Previsao',
        'Acao da TI',
        'Causa raiz',
        'Solucao aplicada',
        'Observacao final',
        'Aberto em',
        'Encerrado em',
    ])

    for ocorrencia in ocorrencias:
        writer.writerow([
            ocorrencia.id,
            ocorrencia.sistema.nome if ocorrencia.sistema else '',
            ocorrencia.unidade.nome if ocorrencia.unidade else 'Geral / Todas as unidades',
            ocorrencia.get_status_display(),
            ocorrencia.get_impacto_display(),
            ocorrencia.titulo,
            ocorrencia.mensagem,
            ocorrencia.previsao,
            ocorrencia.acao_ti,
            ocorrencia.causa_raiz,
            ocorrencia.solucao_aplicada,
            ocorrencia.observacao_encerramento,
            formatar_data_hora_csv(ocorrencia.aberto_em),
            formatar_data_hora_csv(ocorrencia.encerrado_em),
        ])

    return response

@login_required(login_url='/')
def nova_ocorrencia_status(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistemas = SistemaMonitorado.objects.filter(
        ativo=True
    ).order_by(
        'ordem',
        'nome'
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    erro = ''

    if request.method == 'POST':
        sistema_id = request.POST.get('sistema', '').strip()
        unidade_id = request.POST.get('unidade', '').strip()
        status = request.POST.get('status', '').strip()
        impacto = request.POST.get('impacto', '').strip()
        titulo = request.POST.get('titulo', '').strip()
        mensagem = request.POST.get('mensagem', '').strip()
        previsao = request.POST.get('previsao', '').strip()
        acao_ti = request.POST.get('acao_ti', '').strip()

        if not sistema_id or not status or not impacto or not titulo:
            erro = 'Preencha sistema, status, impacto e título.'
        else:
            sistema = get_object_or_404(SistemaMonitorado, id=sistema_id, ativo=True)
            unidade = None

            if unidade_id:
                unidade = get_object_or_404(Unidade, id=unidade_id, ativo=True)

            ocorrencia = OcorrenciaSistema.objects.create(
                sistema=sistema,
                unidade=unidade,
                status=status,
                impacto=impacto,
                titulo=titulo,
                mensagem=mensagem,
                previsao=previsao,
                acao_ti=acao_ti,
                ativo=True,
            )

            registrar_auditoria_status_abertura(request, ocorrencia)

            messages.success(request, 'Ocorrência aberta com sucesso.')
            return redirect('status_sistemas')

    return render(request, 'core/nova_ocorrencia_status.html', {
        'page_title': 'Nova ocorrência de sistema',
        'sistemas': sistemas,
        'unidades': unidades,
        'status_choices': OcorrenciaSistema.STATUS_CHOICES,
        'impacto_choices': OcorrenciaSistema.IMPACTO_CHOICES,
        'erro': erro,
    })

@login_required(login_url='/')
def encerrar_ocorrencia_status(request, ocorrencia_id):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    ocorrencia = get_object_or_404(
        OcorrenciaSistema.objects.select_related('sistema', 'unidade'),
        id=ocorrencia_id,
        ativo=True
    )

    erro = ''

    if request.method == 'POST':
        causa_raiz = request.POST.get('causa_raiz', '').strip()
        solucao_aplicada = request.POST.get('solucao_aplicada', '').strip()
        observacao_encerramento = request.POST.get('observacao_encerramento', '').strip()

        if not causa_raiz or not solucao_aplicada:
            erro = 'Preencha causa raiz e solução aplicada para encerrar a ocorrência.'
        else:
            ocorrencia.causa_raiz = causa_raiz
            ocorrencia.solucao_aplicada = solucao_aplicada
            ocorrencia.observacao_encerramento = observacao_encerramento
            ocorrencia.ativo = False
            ocorrencia.encerrado_em = timezone.now()
            ocorrencia.save()

            registrar_auditoria_status_encerramento(request, ocorrencia)

            messages.success(request, 'Ocorrência encerrada com sucesso.')
            return redirect('status_sistemas')

    return render(request, 'core/encerrar_ocorrencia_status.html', {
        'page_title': f'Encerrar ocorrência #{ocorrencia.id}',
        'ocorrencia': ocorrencia,
        'erro': erro,
    })
