from .common import *


@login_required(login_url='/')
def links_uteis(request):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    links = buscar_links_uteis_filtrados(request, modulo)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    status = request.GET.get('status', '').strip()

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    pode_gerenciar = usuario_pode_gerenciar_links_uteis(request.user)

    return render(request, 'core/links_uteis.html', {
        'page_title': 'Links Úteis',
        'modulo': modulo,
        'links': links,
        'unidades': unidades,
        'busca': busca,
        'unidade_id': unidade_id,
        'status': status,
        'total_links': links.count(),
        'total_ativos': links.filter(ativo=True).count(),
        'total_inativos': links.filter(ativo=False).count() if pode_gerenciar else 0,
        'total_gerais': links.filter(unidade__isnull=True).count(),
        'total_unidade': links.filter(unidade__isnull=False).count(),
        'pode_gerenciar': pode_gerenciar,
    })

@login_required(login_url='/')
def novo_link_util(request):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    form_data = {
        'unidade': '',
        'titulo': '',
        'descricao': '',
        'link_externo': '',
        'ordem': 0,
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_link_util(request)
        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do link.')

        if not form_data['link_externo']:
            erros.append('Informe o endereço do link.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_link_util.html', {
                'page_title': 'Novo link útil',
                'titulo': 'Novo link útil',
                'subtitulo': 'Cadastre um novo sistema, portal ou atalho interno.',
                'form_data': form_data,
                'unidades': unidades,
                'url_salvar': '/portal/modulos/links-uteis/novo/',
                'modo': 'novo',
            })

        link = ConteudoModulo.objects.create(
            modulo=modulo,
            unidade_id=form_data['unidade'] or None,
            tipo='link',
            titulo=form_data['titulo'],
            descricao=form_data['descricao'],
            link_externo=form_data['link_externo'],
            ordem=ordem,
            ativo=form_data['ativo'],
        )

        registrar_auditoria_link_util(
            request=request,
            link=link,
            acao='criado',
            titulo=f'Link útil criado: {link.titulo}'
        )

        messages.success(request, 'Link útil cadastrado com sucesso.')
        return redirect('/portal/modulos/links-uteis/')

    return render(request, 'core/formulario_link_util.html', {
        'page_title': 'Novo link útil',
        'titulo': 'Novo link útil',
        'subtitulo': 'Cadastre um novo sistema, portal ou atalho interno.',
        'form_data': form_data,
        'unidades': unidades,
        'url_salvar': '/portal/modulos/links-uteis/novo/',
        'modo': 'novo',
    })

@login_required(login_url='/')
def editar_link_util(request, link_id):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    link = get_object_or_404(
        ConteudoModulo,
        id=link_id,
        modulo=modulo,
        tipo='link'
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    form_data = link_util_para_form_data(link)

    if request.method == 'POST':
        form_data = montar_form_data_link_util(request)
        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do link.')

        if not form_data['link_externo']:
            erros.append('Informe o endereço do link.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_link_util.html', {
                'page_title': 'Editar link útil',
                'titulo': 'Editar link útil',
                'subtitulo': 'Atualize os dados do link selecionado.',
                'form_data': form_data,
                'link_editado': link,
                'unidades': unidades,
                'url_salvar': f'/portal/modulos/links-uteis/editar/{link.id}/',
                'modo': 'editar',
            })

        link.unidade_id = form_data['unidade'] or None
        link.titulo = form_data['titulo']
        link.descricao = form_data['descricao']
        link.link_externo = form_data['link_externo']
        link.ordem = ordem
        link.ativo = form_data['ativo']
        link.save()

        registrar_auditoria_link_util(
            request=request,
            link=link,
            acao='alterado',
            titulo=f'Link útil alterado: {link.titulo}'
        )

        messages.success(request, 'Link útil atualizado com sucesso.')
        return redirect('/portal/modulos/links-uteis/')

    return render(request, 'core/formulario_link_util.html', {
        'page_title': 'Editar link útil',
        'titulo': 'Editar link útil',
        'subtitulo': 'Atualize os dados do link selecionado.',
        'form_data': form_data,
        'link_editado': link,
        'unidades': unidades,
        'url_salvar': f'/portal/modulos/links-uteis/editar/{link.id}/',
        'modo': 'editar',
    })

@login_required(login_url='/')
def inativar_link_util(request, link_id):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    link = get_object_or_404(
        ConteudoModulo,
        id=link_id,
        modulo=modulo,
        tipo='link'
    )

    link.ativo = False
    link.save()

    registrar_auditoria_link_util(
        request=request,
        link=link,
        acao='alterado',
        titulo=f'Link útil inativado: {link.titulo}'
    )

    messages.success(request, 'Link útil inativado com sucesso.')
    return redirect('/portal/modulos/links-uteis/')

@login_required(login_url='/')
def reativar_link_util(request, link_id):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    link = get_object_or_404(
        ConteudoModulo,
        id=link_id,
        modulo=modulo,
        tipo='link'
    )

    link.ativo = True
    link.save()

    registrar_auditoria_link_util(
        request=request,
        link=link,
        acao='alterado',
        titulo=f'Link útil reativado: {link.titulo}'
    )

    messages.success(request, 'Link útil reativado com sucesso.')
    return redirect('/portal/modulos/links-uteis/')
