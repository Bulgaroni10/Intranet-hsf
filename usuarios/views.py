from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from modulos.models import Modulo
from .models import Usuario, Unidade, Setor


def usuario_tem_acesso_administracao(usuario):
    if not usuario.is_authenticated:
        return False

    if usuario.is_superuser:
        return True

    if usuario.groups.filter(name='TI Administrador').exists():
        return True

    return False


def buscar_dados_formulario_usuario():
    unidades = Unidade.objects.filter(ativo=True).order_by('nome')
    setores = Setor.objects.filter(ativo=True).order_by('nome')
    grupos = Group.objects.all().order_by('name')

    return unidades, setores, grupos


def montar_form_data_usuario(request):
    return {
        'username': request.POST.get('username', '').strip().lower(),
        'first_name': request.POST.get('first_name', '').strip(),
        'last_name': request.POST.get('last_name', '').strip(),
        'email': request.POST.get('email', '').strip().lower(),
        'unidade': request.POST.get('unidade', '').strip(),
        'unidades_permitidas': request.POST.getlist('unidades_permitidas'),
        'setor': request.POST.get('setor', '').strip(),
        'tipo_prestador': request.POST.get('tipo_prestador', 'colaborador').strip(),
        'tipo_conselho': request.POST.get('tipo_conselho', '').strip(),
        'numero_conselho': request.POST.get('numero_conselho', '').strip(),
        'uf_conselho': request.POST.get('uf_conselho', '').strip().upper(),
        'telefone': request.POST.get('telefone', '').strip(),
        'password': request.POST.get('password', ''),
        'password_confirm': request.POST.get('password_confirm', ''),
        'is_active': request.POST.get('is_active') == 'on',
        'primeiro_acesso': request.POST.get('primeiro_acesso') == 'on',
        'is_staff': request.POST.get('is_staff') == 'on',
        'groups': request.POST.getlist('groups'),
    }


def usuario_para_form_data(usuario):
    return {
        'username': usuario.username,
        'first_name': usuario.first_name,
        'last_name': usuario.last_name,
        'email': usuario.email,
        'unidade': str(usuario.unidade_id) if usuario.unidade_id else '',
        'unidades_permitidas': [
            str(unidade.id) for unidade in usuario.unidades_permitidas.all()
        ],
        'setor': str(usuario.setor_id) if usuario.setor_id else '',
        'tipo_prestador': usuario.tipo_prestador,
        'tipo_conselho': usuario.tipo_conselho,
        'numero_conselho': usuario.numero_conselho,
        'uf_conselho': usuario.uf_conselho,
        'telefone': usuario.telefone,
        'is_active': usuario.is_active,
        'primeiro_acesso': usuario.primeiro_acesso,
        'is_staff': usuario.is_staff,
        'groups': [str(grupo.id) for grupo in usuario.groups.all()],
    }


def tratar_erros_validacao(erro):
    mensagens = []

    if hasattr(erro, 'message_dict'):
        for campo, mensagens_campo in erro.message_dict.items():
            for mensagem in mensagens_campo:
                mensagens.append(mensagem)
    else:
        for mensagem in erro.messages:
            mensagens.append(mensagem)

    return mensagens


@login_required(login_url='/login/')
def administracao_intranet(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    total_usuarios = Usuario.objects.count()
    total_usuarios_ativos = Usuario.objects.filter(is_active=True).count()
    total_grupos = Group.objects.count()
    total_unidades = Unidade.objects.count()
    total_setores = Setor.objects.count()
    total_modulos = Modulo.objects.count()
    total_modulos_ativos = Modulo.objects.filter(ativo=True).count()
    total_modulos_restritos = Modulo.objects.filter(
        grupos_permitidos__isnull=False
    ).distinct().count()

    cards_administracao = [
        {
            'icone': '👥',
            'titulo': 'Usuários e Permissões',
            'descricao': 'Criar usuários, editar cadastro, resetar senha e vincular grupos.',
            'link': '/portal/administracao/usuarios/',
            'tag': f'{total_usuarios_ativos} ativos',
        },
        {
            'icone': '👤',
            'titulo': 'Grupos de Acesso',
            'descricao': 'Criar e editar grupos usados nas permissões dos módulos.',
            'link': '/portal/administracao/grupos/',
            'tag': f'{total_grupos} grupos',
        },
        {
            'icone': '🏢',
            'titulo': 'Unidades e Setores',
            'descricao': 'Cadastrar e editar unidades hospitalares e setores internos.',
            'link': '/portal/administracao/unidades-setores/',
            'tag': f'{total_unidades} unidades',
        },
        {
            'icone': '🔐',
            'titulo': 'Permissões por Módulo',
            'descricao': 'Definir quais grupos podem visualizar e acessar cada módulo.',
            'link': '/portal/administracao/permissoes-modulos/',
            'tag': f'{total_modulos_restritos} restritos',
        },
        {
            'icone': '🧾',
            'titulo': 'Auditoria',
            'descricao': 'Consultar registros de ações realizadas nos módulos da intranet.',
            'link': '/portal/modulos/auditoria/',
            'tag': 'Logs',
        },
    ]

    return render(request, 'usuarios/administracao_intranet.html', {
        'cards_administracao': cards_administracao,
        'total_usuarios': total_usuarios,
        'total_usuarios_ativos': total_usuarios_ativos,
        'total_grupos': total_grupos,
        'total_unidades': total_unidades,
        'total_setores': total_setores,
        'total_modulos': total_modulos,
        'total_modulos_ativos': total_modulos_ativos,
        'total_modulos_restritos': total_modulos_restritos,
    })


@login_required(login_url='/login/')
def administracao_usuarios(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    setor_id = request.GET.get('setor', '').strip()
    status = request.GET.get('status', '').strip()

    usuarios = Usuario.objects.select_related(
        'unidade',
        'setor'
    ).prefetch_related(
        'groups',
        'unidades_permitidas',
    ).order_by(
        'first_name',
        'last_name',
        'username'
    )

    if busca:
        usuarios = usuarios.filter(
            Q(first_name__icontains=busca) |
            Q(last_name__icontains=busca) |
            Q(username__icontains=busca) |
            Q(email__icontains=busca) |
            Q(unidade__nome__icontains=busca) |
            Q(unidade__sigla__icontains=busca) |
            Q(unidades_permitidas__nome__icontains=busca) |
            Q(unidades_permitidas__sigla__icontains=busca) |
            Q(setor__nome__icontains=busca)
        ).distinct()

    if unidade_id:
        usuarios = usuarios.filter(
            Q(unidade_id=unidade_id) | Q(unidades_permitidas__id=unidade_id)
        ).distinct()

    if setor_id:
        usuarios = usuarios.filter(setor_id=setor_id)

    if status == 'ativo':
        usuarios = usuarios.filter(is_active=True)
    elif status == 'inativo':
        usuarios = usuarios.filter(is_active=False)

    unidades = Unidade.objects.filter(ativo=True).order_by('nome')
    setores = Setor.objects.filter(ativo=True).order_by('nome')

    total_usuarios = usuarios.count()
    total_ativos = usuarios.filter(is_active=True).count()
    total_inativos = usuarios.filter(is_active=False).count()
    total_admins = usuarios.filter(
        Q(is_superuser=True) |
        Q(groups__name='TI Administrador')
    ).distinct().count()

    return render(request, 'usuarios/administracao_usuarios.html', {
        'usuarios': usuarios,
        'unidades': unidades,
        'setores': setores,
        'busca': busca,
        'unidade_id': unidade_id,
        'setor_id': setor_id,
        'status': status,
        'total_usuarios': total_usuarios,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'total_admins': total_admins,
    })


@login_required(login_url='/login/')
def novo_usuario(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    unidades, setores, grupos = buscar_dados_formulario_usuario()

    form_data = {
        'is_active': True,
        'primeiro_acesso': True,
        'is_staff': False,
        'tipo_prestador': 'colaborador',
        'tipo_conselho': '',
        'groups': [],
        'unidades_permitidas': [],
    }

    if request.method == 'POST':
        form_data = montar_form_data_usuario(request)

        erros = []

        if not form_data['username']:
            erros.append('Informe o login do usuário.')

        if not form_data['first_name']:
            erros.append('Informe o nome.')

        if not form_data['last_name']:
            erros.append('Informe o sobrenome.')

        if not form_data['password']:
            erros.append('Informe a senha inicial.')

        if form_data['password'] != form_data['password_confirm']:
            erros.append('A confirmação da senha não confere.')

        if len(form_data['password']) < 6:
            erros.append('A senha precisa ter pelo menos 6 caracteres.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/novo_usuario.html', {
                'unidades': unidades,
                'setores': setores,
                'grupos': grupos,
                'form_data': form_data,
                'tipo_prestador_choices': Usuario.TIPO_PRESTADOR_CHOICES,
                'tipo_conselho_choices': Usuario.TIPO_CONSELHO_CHOICES,
            })

        try:
            with transaction.atomic():
                usuario = Usuario(
                    username=form_data['username'],
                    first_name=form_data['first_name'],
                    last_name=form_data['last_name'],
                    email=form_data['email'],
                    unidade_id=form_data['unidade'] or None,
                    setor_id=form_data['setor'] or None,
                    tipo_prestador=form_data['tipo_prestador'],
                    tipo_conselho=form_data['tipo_conselho'],
                    numero_conselho=form_data['numero_conselho'],
                    uf_conselho=form_data['uf_conselho'],
                    telefone=form_data['telefone'],
                    is_active=form_data['is_active'],
                    primeiro_acesso=form_data['primeiro_acesso'],
                    is_staff=form_data['is_staff'],
                    is_superuser=False,
                )

                usuario.set_password(form_data['password'])
                usuario.full_clean()
                usuario.save()

                unidades_autorizadas = set(form_data['unidades_permitidas'])
                if form_data['unidade']:
                    unidades_autorizadas.add(form_data['unidade'])
                usuario.unidades_permitidas.set(unidades_autorizadas)

                if form_data['groups']:
                    usuario.groups.set(form_data['groups'])
                else:
                    usuario.groups.clear()

            messages.success(request, 'Usuário cadastrado com sucesso.')
            return redirect('/portal/administracao/usuarios/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível cadastrar o usuário: {erro}')

    return render(request, 'usuarios/novo_usuario.html', {
        'unidades': unidades,
        'setores': setores,
        'grupos': grupos,
        'form_data': form_data,
        'tipo_prestador_choices': Usuario.TIPO_PRESTADOR_CHOICES,
        'tipo_conselho_choices': Usuario.TIPO_CONSELHO_CHOICES,
    })


@login_required(login_url='/login/')
def editar_usuario(request, usuario_id):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    usuario = get_object_or_404(
        Usuario.objects.prefetch_related('groups', 'unidades_permitidas'),
        id=usuario_id
    )

    unidades, setores, grupos = buscar_dados_formulario_usuario()
    form_data = usuario_para_form_data(usuario)

    if request.method == 'POST':
        form_data = montar_form_data_usuario(request)

        erros = []

        if not form_data['username']:
            erros.append('Informe o login do usuário.')

        if not form_data['first_name']:
            erros.append('Informe o nome.')

        if not form_data['last_name']:
            erros.append('Informe o sobrenome.')

        if usuario.is_superuser and not request.user.is_superuser:
            erros.append('Apenas superusuário pode alterar outro superusuário.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/editar_usuario.html', {
                'usuario_editado': usuario,
                'unidades': unidades,
                'setores': setores,
                'grupos': grupos,
                'form_data': form_data,
                'tipo_prestador_choices': Usuario.TIPO_PRESTADOR_CHOICES,
                'tipo_conselho_choices': Usuario.TIPO_CONSELHO_CHOICES,
            })

        try:
            with transaction.atomic():
                usuario.username = form_data['username']
                usuario.first_name = form_data['first_name']
                usuario.last_name = form_data['last_name']
                usuario.email = form_data['email']
                usuario.unidade_id = form_data['unidade'] or None
                usuario.setor_id = form_data['setor'] or None
                usuario.tipo_prestador = form_data['tipo_prestador']
                usuario.tipo_conselho = form_data['tipo_conselho']
                usuario.numero_conselho = form_data['numero_conselho']
                usuario.uf_conselho = form_data['uf_conselho']
                usuario.telefone = form_data['telefone']
                usuario.is_active = form_data['is_active']
                usuario.primeiro_acesso = form_data['primeiro_acesso']
                usuario.is_staff = form_data['is_staff']

                usuario.full_clean()
                usuario.save()

                unidades_autorizadas = set(form_data['unidades_permitidas'])
                if form_data['unidade']:
                    unidades_autorizadas.add(form_data['unidade'])
                usuario.unidades_permitidas.set(unidades_autorizadas)

                if form_data['groups']:
                    usuario.groups.set(form_data['groups'])
                else:
                    usuario.groups.clear()

            messages.success(request, 'Usuário atualizado com sucesso.')
            return redirect('/portal/administracao/usuarios/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível atualizar o usuário: {erro}')

    return render(request, 'usuarios/editar_usuario.html', {
        'usuario_editado': usuario,
        'unidades': unidades,
        'setores': setores,
        'grupos': grupos,
        'form_data': form_data,
        'tipo_prestador_choices': Usuario.TIPO_PRESTADOR_CHOICES,
        'tipo_conselho_choices': Usuario.TIPO_CONSELHO_CHOICES,
    })


@login_required(login_url='/login/')
def resetar_senha_usuario(request, usuario_id):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if usuario.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Apenas superusuário pode resetar senha de outro superusuário.')
        return redirect('/portal/administracao/usuarios/')

    if request.method == 'POST':
        nova_senha = request.POST.get('nova_senha', '')
        confirmar_senha = request.POST.get('confirmar_senha', '')
        marcar_primeiro_acesso = request.POST.get('primeiro_acesso') == 'on'
        manter_ativo = request.POST.get('is_active') == 'on'

        erros = []

        if not nova_senha:
            erros.append('Informe a nova senha.')

        if nova_senha != confirmar_senha:
            erros.append('A confirmação da senha não confere.')

        if len(nova_senha) < 6:
            erros.append('A senha precisa ter pelo menos 6 caracteres.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/resetar_senha_usuario.html', {
                'usuario_editado': usuario,
                'primeiro_acesso': marcar_primeiro_acesso,
                'is_active': manter_ativo,
            })

        usuario.set_password(nova_senha)
        usuario.primeiro_acesso = marcar_primeiro_acesso
        usuario.is_active = manter_ativo
        usuario.save()

        messages.success(request, 'Senha resetada com sucesso.')
        return redirect('/portal/administracao/usuarios/')

    return render(request, 'usuarios/resetar_senha_usuario.html', {
        'usuario_editado': usuario,
        'primeiro_acesso': True,
        'is_active': usuario.is_active,
    })


@login_required(login_url='/login/')
def administracao_unidades_setores(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    busca = request.GET.get('busca', '').strip()
    status = request.GET.get('status', '').strip()

    unidades = Unidade.objects.all().order_by('nome')
    setores = Setor.objects.all().order_by('nome')

    if busca:
        unidades = unidades.filter(
            Q(nome__icontains=busca) |
            Q(sigla__icontains=busca)
        )
        setores = setores.filter(Q(nome__icontains=busca))

    if status == 'ativo':
        unidades = unidades.filter(ativo=True)
        setores = setores.filter(ativo=True)
    elif status == 'inativo':
        unidades = unidades.filter(ativo=False)
        setores = setores.filter(ativo=False)

    total_unidades = unidades.count()
    total_unidades_ativas = unidades.filter(ativo=True).count()
    total_unidades_inativas = unidades.filter(ativo=False).count()

    total_setores = setores.count()
    total_setores_ativos = setores.filter(ativo=True).count()
    total_setores_inativos = setores.filter(ativo=False).count()

    return render(request, 'usuarios/administracao_unidades_setores.html', {
        'unidades': unidades,
        'setores': setores,
        'busca': busca,
        'status': status,
        'total_unidades': total_unidades,
        'total_unidades_ativas': total_unidades_ativas,
        'total_unidades_inativas': total_unidades_inativas,
        'total_setores': total_setores,
        'total_setores_ativos': total_setores_ativos,
        'total_setores_inativos': total_setores_inativos,
    })


@login_required(login_url='/login/')
def nova_unidade(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'nome': '',
        'sigla': '',
        'codigo_mv': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = {
            'nome': request.POST.get('nome', '').strip(),
            'sigla': request.POST.get('sigla', '').strip().upper(),
            'codigo_mv': request.POST.get('codigo_mv', '').strip(),
            'ativo': request.POST.get('ativo') == 'on',
        }

        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome da unidade.')

        if not form_data['sigla']:
            erros.append('Informe a sigla da unidade.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/formulario_unidade.html', {
                'titulo': 'Nova unidade',
                'subtitulo': 'Cadastre uma nova unidade para uso nos módulos da intranet.',
                'form_data': form_data,
                'url_salvar': '/portal/administracao/unidades-setores/unidade/nova/',
                'modo': 'novo',
            })

        try:
            unidade = Unidade(
                nome=form_data['nome'],
                sigla=form_data['sigla'],
                codigo_mv=form_data['codigo_mv'] or None,
                ativo=form_data['ativo'],
            )

            unidade.full_clean()
            unidade.save()

            messages.success(request, 'Unidade cadastrada com sucesso.')
            return redirect('/portal/administracao/unidades-setores/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível cadastrar a unidade: {erro}')

    return render(request, 'usuarios/formulario_unidade.html', {
        'titulo': 'Nova unidade',
        'subtitulo': 'Cadastre uma nova unidade para uso nos módulos da intranet.',
        'form_data': form_data,
        'url_salvar': '/portal/administracao/unidades-setores/unidade/nova/',
        'modo': 'novo',
    })


@login_required(login_url='/login/')
def editar_unidade(request, unidade_id):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    unidade = get_object_or_404(Unidade, id=unidade_id)

    form_data = {
        'nome': unidade.nome,
        'sigla': unidade.sigla,
        'codigo_mv': unidade.codigo_mv or '',
        'ativo': unidade.ativo,
    }

    if request.method == 'POST':
        form_data = {
            'nome': request.POST.get('nome', '').strip(),
            'sigla': request.POST.get('sigla', '').strip().upper(),
            'codigo_mv': request.POST.get('codigo_mv', '').strip(),
            'ativo': request.POST.get('ativo') == 'on',
        }

        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome da unidade.')

        if not form_data['sigla']:
            erros.append('Informe a sigla da unidade.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/formulario_unidade.html', {
                'titulo': 'Editar unidade',
                'subtitulo': 'Atualize os dados da unidade selecionada.',
                'unidade_editada': unidade,
                'form_data': form_data,
                'url_salvar': f'/portal/administracao/unidades-setores/unidade/editar/{unidade.id}/',
                'modo': 'editar',
            })

        try:
            unidade.nome = form_data['nome']
            unidade.sigla = form_data['sigla']
            unidade.codigo_mv = form_data['codigo_mv'] or None
            unidade.ativo = form_data['ativo']

            unidade.full_clean()
            unidade.save()

            messages.success(request, 'Unidade atualizada com sucesso.')
            return redirect('/portal/administracao/unidades-setores/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível atualizar a unidade: {erro}')

    return render(request, 'usuarios/formulario_unidade.html', {
        'titulo': 'Editar unidade',
        'subtitulo': 'Atualize os dados da unidade selecionada.',
        'unidade_editada': unidade,
        'form_data': form_data,
        'url_salvar': f'/portal/administracao/unidades-setores/unidade/editar/{unidade.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/login/')
def novo_setor(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'nome': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = {
            'nome': request.POST.get('nome', '').strip(),
            'ativo': request.POST.get('ativo') == 'on',
        }

        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do setor.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/formulario_setor.html', {
                'titulo': 'Novo setor',
                'subtitulo': 'Cadastre um novo setor para vincular usuários, documentos, ramais e permissões.',
                'form_data': form_data,
                'url_salvar': '/portal/administracao/unidades-setores/setor/novo/',
                'modo': 'novo',
            })

        try:
            setor = Setor(
                nome=form_data['nome'],
                ativo=form_data['ativo'],
            )

            setor.full_clean()
            setor.save()

            messages.success(request, 'Setor cadastrado com sucesso.')
            return redirect('/portal/administracao/unidades-setores/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível cadastrar o setor: {erro}')

    return render(request, 'usuarios/formulario_setor.html', {
        'titulo': 'Novo setor',
        'subtitulo': 'Cadastre um novo setor para vincular usuários, documentos, ramais e permissões.',
        'form_data': form_data,
        'url_salvar': '/portal/administracao/unidades-setores/setor/novo/',
        'modo': 'novo',
    })


@login_required(login_url='/login/')
def editar_setor(request, setor_id):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    setor = get_object_or_404(Setor, id=setor_id)

    form_data = {
        'nome': setor.nome,
        'ativo': setor.ativo,
    }

    if request.method == 'POST':
        form_data = {
            'nome': request.POST.get('nome', '').strip(),
            'ativo': request.POST.get('ativo') == 'on',
        }

        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do setor.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/formulario_setor.html', {
                'titulo': 'Editar setor',
                'subtitulo': 'Atualize os dados do setor selecionado.',
                'setor_editado': setor,
                'form_data': form_data,
                'url_salvar': f'/portal/administracao/unidades-setores/setor/editar/{setor.id}/',
                'modo': 'editar',
            })

        try:
            setor.nome = form_data['nome']
            setor.ativo = form_data['ativo']

            setor.full_clean()
            setor.save()

            messages.success(request, 'Setor atualizado com sucesso.')
            return redirect('/portal/administracao/unidades-setores/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível atualizar o setor: {erro}')

    return render(request, 'usuarios/formulario_setor.html', {
        'titulo': 'Editar setor',
        'subtitulo': 'Atualize os dados do setor selecionado.',
        'setor_editado': setor,
        'form_data': form_data,
        'url_salvar': f'/portal/administracao/unidades-setores/setor/editar/{setor.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/login/')
def administracao_permissoes_modulos(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    busca = request.GET.get('busca', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    status = request.GET.get('status', '').strip()
    acesso = request.GET.get('acesso', '').strip()

    modulos = Modulo.objects.prefetch_related(
        'grupos_permitidos'
    ).order_by(
        'categoria',
        'ordem',
        'nome'
    )

    if busca:
        modulos = modulos.filter(
            Q(nome__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(link__icontains=busca) |
            Q(tag__icontains=busca)
        )

    if categoria:
        modulos = modulos.filter(categoria=categoria)

    if status == 'ativo':
        modulos = modulos.filter(ativo=True)
    elif status == 'inativo':
        modulos = modulos.filter(ativo=False)

    if acesso == 'livre':
        modulos = modulos.filter(grupos_permitidos__isnull=True)
    elif acesso == 'restrito':
        modulos = modulos.filter(grupos_permitidos__isnull=False).distinct()

    total_modulos = modulos.count()
    total_ativos = modulos.filter(ativo=True).count()
    total_inativos = modulos.filter(ativo=False).count()
    total_restritos = modulos.filter(grupos_permitidos__isnull=False).distinct().count()
    total_livres = modulos.filter(grupos_permitidos__isnull=True).count()

    return render(request, 'usuarios/administracao_permissoes_modulos.html', {
        'modulos': modulos,
        'categorias': Modulo.CATEGORIA_CHOICES,
        'busca': busca,
        'categoria': categoria,
        'status': status,
        'acesso': acesso,
        'total_modulos': total_modulos,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'total_restritos': total_restritos,
        'total_livres': total_livres,
    })


@login_required(login_url='/login/')
def editar_permissao_modulo(request, modulo_id):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = get_object_or_404(
        Modulo.objects.prefetch_related('grupos_permitidos'),
        id=modulo_id
    )

    grupos = Group.objects.all().order_by('name')

    form_data = {
        'ativo': modulo.ativo,
        'acesso_livre': not modulo.grupos_permitidos.exists(),
        'groups': [str(grupo.id) for grupo in modulo.grupos_permitidos.all()],
    }

    if request.method == 'POST':
        form_data = {
            'ativo': request.POST.get('ativo') == 'on',
            'acesso_livre': request.POST.get('acesso_livre') == 'on',
            'groups': request.POST.getlist('groups'),
        }

        erros = []

        if not form_data['acesso_livre'] and not form_data['groups']:
            erros.append(
                'Selecione pelo menos um grupo ou marque a opção "Liberado para todos".'
            )

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/formulario_permissao_modulo.html', {
                'modulo': modulo,
                'grupos': grupos,
                'form_data': form_data,
            })

        try:
            with transaction.atomic():
                modulo.ativo = form_data['ativo']
                modulo.save()

                if form_data['acesso_livre']:
                    modulo.grupos_permitidos.clear()
                else:
                    modulo.grupos_permitidos.set(form_data['groups'])

            messages.success(request, 'Permissões do módulo atualizadas com sucesso.')
            return redirect('/portal/administracao/permissoes-modulos/')

        except Exception as erro:
            messages.error(request, f'Não foi possível atualizar as permissões: {erro}')

    return render(request, 'usuarios/formulario_permissao_modulo.html', {
        'modulo': modulo,
        'grupos': grupos,
        'form_data': form_data,
    })


@login_required(login_url='/login/')
def administracao_grupos(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    busca = request.GET.get('busca', '').strip()

    grupos = Group.objects.all().order_by('name')

    if busca:
        grupos = grupos.filter(name__icontains=busca)

    for grupo in grupos:
        grupo.total_usuarios = Usuario.objects.filter(groups=grupo).count()
        grupo.total_modulos = Modulo.objects.filter(grupos_permitidos=grupo).count()

    total_grupos = grupos.count()
    total_usuarios_com_grupo = Usuario.objects.filter(groups__isnull=False).distinct().count()
    total_modulos_restritos = Modulo.objects.filter(grupos_permitidos__isnull=False).distinct().count()

    return render(request, 'usuarios/administracao_grupos.html', {
        'grupos': grupos,
        'busca': busca,
        'total_grupos': total_grupos,
        'total_usuarios_com_grupo': total_usuarios_com_grupo,
        'total_modulos_restritos': total_modulos_restritos,
    })


@login_required(login_url='/login/')
def novo_grupo(request):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'name': '',
    }

    if request.method == 'POST':
        form_data = {
            'name': request.POST.get('name', '').strip(),
        }

        erros = []

        if not form_data['name']:
            erros.append('Informe o nome do grupo.')

        if Group.objects.filter(name__iexact=form_data['name']).exists():
            erros.append('Já existe um grupo com esse nome.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/formulario_grupo.html', {
                'titulo': 'Novo grupo',
                'subtitulo': 'Cadastre um grupo para controlar acesso aos módulos da intranet.',
                'form_data': form_data,
                'url_salvar': '/portal/administracao/grupos/novo/',
                'modo': 'novo',
            })

        try:
            Group.objects.create(name=form_data['name'])

            messages.success(request, 'Grupo cadastrado com sucesso.')
            return redirect('/portal/administracao/grupos/')

        except Exception as erro:
            messages.error(request, f'Não foi possível cadastrar o grupo: {erro}')

    return render(request, 'usuarios/formulario_grupo.html', {
        'titulo': 'Novo grupo',
        'subtitulo': 'Cadastre um grupo para controlar acesso aos módulos da intranet.',
        'form_data': form_data,
        'url_salvar': '/portal/administracao/grupos/novo/',
        'modo': 'novo',
    })


@login_required(login_url='/login/')
def editar_grupo(request, grupo_id):
    if not usuario_tem_acesso_administracao(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    grupo = get_object_or_404(Group, id=grupo_id)

    form_data = {
        'name': grupo.name,
    }

    if request.method == 'POST':
        form_data = {
            'name': request.POST.get('name', '').strip(),
        }

        erros = []

        if not form_data['name']:
            erros.append('Informe o nome do grupo.')

        if grupo.name == 'TI Administrador' and form_data['name'] != 'TI Administrador':
            erros.append(
                'O grupo TI Administrador não pode ser renomeado, pois ele controla o acesso administrativo da intranet.'
            )

        if Group.objects.filter(name__iexact=form_data['name']).exclude(id=grupo.id).exists():
            erros.append('Já existe outro grupo com esse nome.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'usuarios/formulario_grupo.html', {
                'titulo': 'Editar grupo',
                'subtitulo': 'Atualize o nome do grupo selecionado.',
                'grupo_editado': grupo,
                'form_data': form_data,
                'url_salvar': f'/portal/administracao/grupos/editar/{grupo.id}/',
                'modo': 'editar',
            })

        try:
            grupo.name = form_data['name']
            grupo.save()

            messages.success(request, 'Grupo atualizado com sucesso.')
            return redirect('/portal/administracao/grupos/')

        except Exception as erro:
            messages.error(request, f'Não foi possível atualizar o grupo: {erro}')

    return render(request, 'usuarios/formulario_grupo.html', {
        'titulo': 'Editar grupo',
        'subtitulo': 'Atualize o nome do grupo selecionado.',
        'grupo_editado': grupo,
        'form_data': form_data,
        'url_salvar': f'/portal/administracao/grupos/editar/{grupo.id}/',
        'modo': 'editar',
    })
