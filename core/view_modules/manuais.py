from .common import *


@login_required(login_url='/')
def manuais_procedimentos(request):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudos = buscar_manuais_filtrados(request, modulo)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    status = request.GET.get('status', '').strip()

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    tipos_conteudo = ConteudoModulo.TIPO_CHOICES
    pode_gerenciar = usuario_pode_gerenciar_manuais(request.user)

    return render(request, 'core/manuais_procedimentos.html', {
        'page_title': 'Manuais e Procedimentos',
        'modulo': modulo,
        'conteudos': conteudos,
        'unidades': unidades,
        'tipos_conteudo': tipos_conteudo,
        'busca': busca,
        'unidade_id': unidade_id,
        'tipo': tipo,
        'status': status,
        'total_conteudos': conteudos.count(),
        'total_ativos': conteudos.filter(ativo=True).count(),
        'total_inativos': conteudos.filter(ativo=False).count() if pode_gerenciar else 0,
        'total_gerais': conteudos.filter(unidade__isnull=True).count(),
        'total_com_arquivo': conteudos.exclude(arquivo='').filter(arquivo__isnull=False).count(),
        'total_com_link': conteudos.exclude(link_externo='').count(),
        'pode_gerenciar': pode_gerenciar,
    })

@login_required(login_url='/')
def novo_manual_procedimento(request):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    grupos = Group.objects.all().order_by('name')

    form_data = {
        'unidade': '',
        'tipo': 'manual',
        'titulo': '',
        'descricao': '',
        'link_externo': '',
        'ordem': 0,
        'ativo': True,
        'remover_arquivo': False,
        'grupos_permitidos': [],
    }

    if request.method == 'POST':
        form_data = montar_form_data_manual(request)
        arquivo = request.FILES.get('arquivo')

        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do conteúdo.')

        if not form_data['tipo']:
            erros.append('Informe o tipo do conteúdo.')

        if not arquivo and not form_data['link_externo'] and form_data['tipo'] not in ['observacao']:
            erros.append('Informe um arquivo ou um link externo.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_manual_procedimento.html', {
                'page_title': 'Novo manual / procedimento',
                'titulo': 'Novo manual / procedimento',
                'subtitulo': 'Cadastre um manual, POP, procedimento, link, contingência ou observação.',
                'form_data': form_data,
                'unidades': unidades,
                'grupos': grupos,
                'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
                'url_salvar': '/portal/modulos/manuais-procedimentos/novo/',
                'modo': 'novo',
            })

        conteudo = ConteudoModulo.objects.create(
            modulo=modulo,
            unidade_id=form_data['unidade'] or None,
            tipo=form_data['tipo'],
            titulo=form_data['titulo'],
            descricao=form_data['descricao'],
            arquivo=arquivo,
            link_externo=form_data['link_externo'],
            ordem=ordem,
            ativo=form_data['ativo'],
        )

        if form_data['grupos_permitidos']:
            conteudo.grupos_permitidos.set(form_data['grupos_permitidos'])
        else:
            conteudo.grupos_permitidos.clear()

        registrar_auditoria_manual(
            request=request,
            conteudo=conteudo,
            acao='criado',
            titulo=f'Manual / procedimento criado: {conteudo.titulo}'
        )

        messages.success(request, 'Manual / procedimento cadastrado com sucesso.')
        return redirect('/portal/modulos/manuais-procedimentos/')

    return render(request, 'core/formulario_manual_procedimento.html', {
        'page_title': 'Novo manual / procedimento',
        'titulo': 'Novo manual / procedimento',
        'subtitulo': 'Cadastre um manual, POP, procedimento, link, contingência ou observação.',
        'form_data': form_data,
        'unidades': unidades,
        'grupos': grupos,
        'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
        'url_salvar': '/portal/modulos/manuais-procedimentos/novo/',
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_manual_procedimento(request, conteudo_id):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudo = get_object_or_404(
        ConteudoModulo.objects.prefetch_related('grupos_permitidos'),
        id=conteudo_id,
        modulo=modulo
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    grupos = Group.objects.all().order_by('name')
    form_data = manual_para_form_data(conteudo)

    if request.method == 'POST':
        form_data = montar_form_data_manual(request)
        arquivo = request.FILES.get('arquivo')

        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do conteúdo.')

        if not form_data['tipo']:
            erros.append('Informe o tipo do conteúdo.')

        arquivo_atual_sera_removido = form_data['remover_arquivo']
        tem_arquivo_final = bool(arquivo) or (bool(conteudo.arquivo) and not arquivo_atual_sera_removido)

        if not tem_arquivo_final and not form_data['link_externo'] and form_data['tipo'] not in ['observacao']:
            erros.append('Informe um arquivo ou um link externo.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_manual_procedimento.html', {
                'page_title': 'Editar manual / procedimento',
                'titulo': 'Editar manual / procedimento',
                'subtitulo': 'Atualize os dados do conteúdo selecionado.',
                'form_data': form_data,
                'conteudo_editado': conteudo,
                'unidades': unidades,
                'grupos': grupos,
                'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
                'url_salvar': f'/portal/modulos/manuais-procedimentos/editar/{conteudo.id}/',
                'modo': 'editar',
            })

        conteudo.unidade_id = form_data['unidade'] or None
        conteudo.tipo = form_data['tipo']
        conteudo.titulo = form_data['titulo']
        conteudo.descricao = form_data['descricao']
        conteudo.link_externo = form_data['link_externo']
        conteudo.ordem = ordem
        conteudo.ativo = form_data['ativo']

        if form_data['remover_arquivo']:
            conteudo.arquivo = None

        if arquivo:
            conteudo.arquivo = arquivo

        conteudo.save()

        if form_data['grupos_permitidos']:
            conteudo.grupos_permitidos.set(form_data['grupos_permitidos'])
        else:
            conteudo.grupos_permitidos.clear()

        registrar_auditoria_manual(
            request=request,
            conteudo=conteudo,
            acao='alterado',
            titulo=f'Manual / procedimento alterado: {conteudo.titulo}'
        )

        messages.success(request, 'Manual / procedimento atualizado com sucesso.')
        return redirect('/portal/modulos/manuais-procedimentos/')

    return render(request, 'core/formulario_manual_procedimento.html', {
        'page_title': 'Editar manual / procedimento',
        'titulo': 'Editar manual / procedimento',
        'subtitulo': 'Atualize os dados do conteúdo selecionado.',
        'form_data': form_data,
        'conteudo_editado': conteudo,
        'unidades': unidades,
        'grupos': grupos,
        'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
        'url_salvar': f'/portal/modulos/manuais-procedimentos/editar/{conteudo.id}/',
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_manual_procedimento(request, conteudo_id):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudo = get_object_or_404(
        ConteudoModulo,
        id=conteudo_id,
        modulo=modulo
    )

    conteudo.ativo = False
    conteudo.save()

    registrar_auditoria_manual(
        request=request,
        conteudo=conteudo,
        acao='alterado',
        titulo=f'Manual / procedimento inativado: {conteudo.titulo}'
    )

    messages.success(request, 'Manual / procedimento inativado com sucesso.')
    return redirect('/portal/modulos/manuais-procedimentos/')

@login_required(login_url='/')
def reativar_manual_procedimento(request, conteudo_id):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudo = get_object_or_404(
        ConteudoModulo,
        id=conteudo_id,
        modulo=modulo
    )

    conteudo.ativo = True
    conteudo.save()

    registrar_auditoria_manual(
        request=request,
        conteudo=conteudo,
        acao='alterado',
        titulo=f'Manual / procedimento reativado: {conteudo.titulo}'
    )

    messages.success(request, 'Manual / procedimento reativado com sucesso.')
    return redirect('/portal/modulos/manuais-procedimentos/')
