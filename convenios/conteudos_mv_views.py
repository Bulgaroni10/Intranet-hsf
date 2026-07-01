from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from auditoria.models import RegistroAuditoria
from conteudos.models import ConteudoModulo
from modulos.models import Modulo
from usuarios.models import Unidade


TIPOS_CONTEUDO_MV = {
    'contingencia': {
        'titulo_lista': 'Contingência MV',
        'titulo_form_novo': 'Nova contingência MV',
        'titulo_form_editar': 'Editar contingência MV',
        'url_lista': '/portal/modulos/mv/contingencia/',
        'icone': '🚨',
        'etiqueta': 'Contingência',
    },
    'chamado': {
        'titulo_lista': 'Chamados MV',
        'titulo_form_novo': 'Novo chamado MV',
        'titulo_form_editar': 'Editar chamado MV',
        'url_lista': '/portal/modulos/mv/chamados/',
        'icone': '🧾',
        'etiqueta': 'Chamado MV',
    },
    'link': {
        'titulo_lista': 'Links úteis MV',
        'titulo_form_novo': 'Novo link útil MV',
        'titulo_form_editar': 'Editar link útil MV',
        'url_lista': '/portal/modulos/mv/links/',
        'icone': '🔗',
        'etiqueta': 'Link útil',
    },
    'observacao': {
        'titulo_lista': 'Observações MV',
        'titulo_form_novo': 'Nova observação MV',
        'titulo_form_editar': 'Editar observação MV',
        'url_lista': '/portal/modulos/mv/observacoes/',
        'icone': '📝',
        'etiqueta': 'Observação',
    },
}


def usuario_eh_admin_ti(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def usuario_pode_gerenciar_mv(user):
    return usuario_eh_admin_ti(user)


def obter_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def obter_modulo_mv():
    return get_object_or_404(
        Modulo,
        nome='MV / Sistema Hospitalar',
        ativo=True
    )


def obter_config_tipo(tipo):
    return TIPOS_CONTEUDO_MV.get(tipo)


def redirecionar_lista_tipo(tipo):
    config = obter_config_tipo(tipo)

    if not config:
        return '/portal/modulos/mv/'

    return config['url_lista']


def registrar_auditoria_conteudo_mv(request, conteudo, acao, titulo):
    RegistroAuditoria.objects.create(
        modulo='conteudos',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Título: {conteudo.titulo}\n'
            f'Tipo: {conteudo.get_tipo_display()}\n'
            f'Unidade: {conteudo.unidade.nome if conteudo.unidade else "Todas"}\n'
            f'Ativo: {"Sim" if conteudo.ativo else "Não"}\n'
            f'Link externo: {conteudo.link_externo or "Não informado"}\n'
            f'Arquivo: {conteudo.arquivo.name if conteudo.arquivo else "Não informado"}'
        ),
        modelo='ConteudoModulo',
        objeto_id=str(conteudo.id),
        usuario=request.user,
        unidade=getattr(request.user, 'unidade', None),
        ip_origem=obter_ip_cliente(request),
    )


def montar_form_data(request):
    return {
        'titulo': request.POST.get('titulo', '').strip(),
        'descricao': request.POST.get('descricao', '').strip(),
        'unidade': request.POST.get('unidade', '').strip(),
        'link_externo': request.POST.get('link_externo', '').strip(),
        'ordem': request.POST.get('ordem', '0').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def conteudo_para_form_data(conteudo):
    return {
        'titulo': conteudo.titulo,
        'descricao': conteudo.descricao,
        'unidade': str(conteudo.unidade_id) if conteudo.unidade_id else '',
        'link_externo': conteudo.link_externo,
        'ordem': str(conteudo.ordem),
        'ativo': conteudo.ativo,
    }


def validar_form_data(form_data):
    erros = []

    if not form_data['titulo']:
        erros.append('Informe o título.')

    if form_data['link_externo']:
        if not form_data['link_externo'].startswith('http://') and not form_data['link_externo'].startswith('https://'):
            erros.append('O link externo deve começar com http:// ou https://.')

    try:
        ordem = int(form_data['ordem'] or 0)

        if ordem < 0:
            erros.append('A ordem não pode ser negativa.')

    except ValueError:
        erros.append('A ordem precisa ser um número.')

    return erros


def obter_unidades_ativas():
    return Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )


@login_required(login_url='/')
def novo_conteudo_mv(request, tipo):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    config = obter_config_tipo(tipo)

    if not config:
        messages.error(request, 'Tipo de conteúdo MV inválido.')
        return redirect('/portal/modulos/mv/')

    modulo = obter_modulo_mv()
    unidades = obter_unidades_ativas()

    form_data = {
        'titulo': '',
        'descricao': '',
        'unidade': '',
        'link_externo': '',
        'ordem': '0',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data(request)
        erros = validar_form_data(form_data)

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'convenios/formulario_conteudo_mv.html', {
                'modo': 'novo',
                'tipo': tipo,
                'config': config,
                'form_data': form_data,
                'unidades': unidades,
                'modulo': modulo,
            })

        unidade = None

        if form_data['unidade']:
            unidade = get_object_or_404(Unidade, id=form_data['unidade'])

        conteudo = ConteudoModulo.objects.create(
            modulo=modulo,
            unidade=unidade,
            tipo=tipo,
            titulo=form_data['titulo'],
            descricao=form_data['descricao'],
            link_externo=form_data['link_externo'],
            arquivo=request.FILES.get('arquivo'),
            ordem=int(form_data['ordem'] or 0),
            ativo=form_data['ativo'],
        )

        registrar_auditoria_conteudo_mv(
            request=request,
            conteudo=conteudo,
            acao='criado',
            titulo=f'Conteúdo MV criado: {conteudo.titulo}',
        )

        messages.success(request, 'Conteúdo cadastrado com sucesso.')
        return redirect(config['url_lista'])

    return render(request, 'convenios/formulario_conteudo_mv.html', {
        'modo': 'novo',
        'tipo': tipo,
        'config': config,
        'form_data': form_data,
        'unidades': unidades,
        'modulo': modulo,
    })


@login_required(login_url='/')
def editar_conteudo_mv(request, conteudo_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    conteudo = get_object_or_404(
        ConteudoModulo.objects.select_related('modulo', 'unidade'),
        id=conteudo_id,
        modulo__nome='MV / Sistema Hospitalar'
    )

    config = obter_config_tipo(conteudo.tipo)

    if not config:
        messages.error(request, 'Tipo de conteúdo MV inválido.')
        return redirect('/portal/modulos/mv/')

    unidades = obter_unidades_ativas()
    form_data = conteudo_para_form_data(conteudo)

    if request.method == 'POST':
        form_data = montar_form_data(request)
        erros = validar_form_data(form_data)

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'convenios/formulario_conteudo_mv.html', {
                'modo': 'editar',
                'tipo': conteudo.tipo,
                'config': config,
                'form_data': form_data,
                'unidades': unidades,
                'modulo': conteudo.modulo,
                'conteudo': conteudo,
            })

        unidade = None

        if form_data['unidade']:
            unidade = get_object_or_404(Unidade, id=form_data['unidade'])

        conteudo.unidade = unidade
        conteudo.titulo = form_data['titulo']
        conteudo.descricao = form_data['descricao']
        conteudo.link_externo = form_data['link_externo']
        conteudo.ordem = int(form_data['ordem'] or 0)
        conteudo.ativo = form_data['ativo']

        novo_arquivo = request.FILES.get('arquivo')

        if novo_arquivo:
            conteudo.arquivo = novo_arquivo

        conteudo.save()

        registrar_auditoria_conteudo_mv(
            request=request,
            conteudo=conteudo,
            acao='alterado',
            titulo=f'Conteúdo MV alterado: {conteudo.titulo}',
        )

        messages.success(request, 'Conteúdo atualizado com sucesso.')
        return redirect(config['url_lista'])

    return render(request, 'convenios/formulario_conteudo_mv.html', {
        'modo': 'editar',
        'tipo': conteudo.tipo,
        'config': config,
        'form_data': form_data,
        'unidades': unidades,
        'modulo': conteudo.modulo,
        'conteudo': conteudo,
    })


@login_required(login_url='/')
def inativar_conteudo_mv(request, conteudo_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    conteudo = get_object_or_404(
        ConteudoModulo.objects.select_related('modulo'),
        id=conteudo_id,
        modulo__nome='MV / Sistema Hospitalar'
    )

    conteudo.ativo = False
    conteudo.save()

    registrar_auditoria_conteudo_mv(
        request=request,
        conteudo=conteudo,
        acao='alterado',
        titulo=f'Conteúdo MV inativado: {conteudo.titulo}',
    )

    messages.success(request, 'Conteúdo inativado com sucesso.')
    return redirect(redirecionar_lista_tipo(conteudo.tipo))


@login_required(login_url='/')
def reativar_conteudo_mv(request, conteudo_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    conteudo = get_object_or_404(
        ConteudoModulo.objects.select_related('modulo'),
        id=conteudo_id,
        modulo__nome='MV / Sistema Hospitalar'
    )

    conteudo.ativo = True
    conteudo.save()

    registrar_auditoria_conteudo_mv(
        request=request,
        conteudo=conteudo,
        acao='alterado',
        titulo=f'Conteúdo MV reativado: {conteudo.titulo}',
    )

    messages.success(request, 'Conteúdo reativado com sucesso.')
    return redirect(redirecionar_lista_tipo(conteudo.tipo))