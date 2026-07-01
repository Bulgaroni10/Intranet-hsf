from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from modulos.models import Modulo
from usuarios.models import Unidade
from .models import AvisoComunicado


NOME_MODULO_AVISOS = 'Avisos / Comunicados'


def usuario_pode_acessar_modulo(user, nome_modulo):
    if user.is_superuser or user.groups.filter(name='TI Administrador').exists():
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


def usuario_pode_gerenciar_avisos(user):
    if user.is_superuser:
        return True

    if user.groups.filter(name='TI Administrador').exists():
        return True

    return False


def usuario_eh_admin_ti(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def obter_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def registrar_auditoria_aviso(request, aviso, acao, titulo):
    unidades_compartilhadas = ', '.join(
        aviso.unidades_compartilhadas.values_list('sigla', flat=True)
    ) or 'Nenhuma'

    grupos = ', '.join(
        aviso.grupos_permitidos.values_list('name', flat=True)
    ) or 'Todos os grupos com acesso ao módulo'

    RegistroAuditoria.objects.create(
        modulo='avisos',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Título: {aviso.titulo}\n'
            f'Tipo: {aviso.get_tipo_display()}\n'
            f'Prioridade: {aviso.get_prioridade_display()}\n'
            f'Unidade principal: {aviso.unidade.nome if aviso.unidade else "Geral / Todas as unidades"}\n'
            f'Unidades compartilhadas: {unidades_compartilhadas}\n'
            f'Grupos permitidos: {grupos}\n'
            f'Fixado no topo: {"Sim" if aviso.fixar_no_topo else "Não"}\n'
            f'Exibir no dashboard: {"Sim" if aviso.exibir_no_dashboard else "Não"}\n'
            f'Ativo: {"Sim" if aviso.ativo else "Não"}\n'
            f'Expira em: {timezone.localtime(aviso.expira_em).strftime("%d/%m/%Y %H:%M") if aviso.expira_em else "Não informado"}'
        ),
        modelo='AvisoComunicado',
        objeto_id=str(aviso.id),
        usuario=request.user,
        unidade=aviso.unidade,
        ip_origem=obter_ip_cliente(request),
    )


def buscar_avisos_visiveis(user):
    agora = timezone.now()

    avisos = AvisoComunicado.objects.filter(
        ativo=True,
        publicado_em__lte=agora,
    ).filter(
        Q(expira_em__isnull=True) |
        Q(expira_em__gte=agora)
    )

    if usuario_eh_admin_ti(user):
        return avisos.select_related(
            'unidade',
            'criado_por'
        ).prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ).order_by(
            '-fixar_no_topo',
            '-publicado_em',
            'titulo'
        )

    avisos = avisos.filter(
        Q(unidade=user.unidade) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=user.unidade)
    )

    grupos_usuario = user.groups.all()

    return avisos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().select_related(
        'unidade',
        'criado_por'
    ).prefetch_related(
        'grupos_permitidos',
        'unidades_compartilhadas'
    ).order_by(
        '-fixar_no_topo',
        '-publicado_em',
        'titulo'
    )


def buscar_avisos_para_gestao(user):
    avisos = AvisoComunicado.objects.all()

    if usuario_eh_admin_ti(user):
        return avisos.select_related(
            'unidade',
            'criado_por'
        ).prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ).order_by(
            '-ativo',
            '-fixar_no_topo',
            '-publicado_em',
            'titulo'
        )

    return avisos.filter(
        Q(unidade=user.unidade) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=user.unidade)
    ).distinct().select_related(
        'unidade',
        'criado_por'
    ).prefetch_related(
        'grupos_permitidos',
        'unidades_compartilhadas'
    ).order_by(
        '-ativo',
        '-fixar_no_topo',
        '-publicado_em',
        'titulo'
    )


def montar_form_data_aviso(request):
    return {
        'titulo': request.POST.get('titulo', '').strip(),
        'tipo': request.POST.get('tipo', '').strip(),
        'prioridade': request.POST.get('prioridade', '').strip(),
        'unidade': request.POST.get('unidade', '').strip(),
        'unidades_compartilhadas': request.POST.getlist('unidades_compartilhadas'),
        'grupos_permitidos': request.POST.getlist('grupos_permitidos'),
        'resumo': request.POST.get('resumo', '').strip(),
        'mensagem': request.POST.get('mensagem', '').strip(),
        'link_externo': request.POST.get('link_externo', '').strip(),
        'expira_em': request.POST.get('expira_em', '').strip(),
        'fixar_no_topo': request.POST.get('fixar_no_topo') == 'on',
        'exibir_no_dashboard': request.POST.get('exibir_no_dashboard') == 'on',
        'ativo': request.POST.get('ativo') == 'on',
        'remover_arquivo': request.POST.get('remover_arquivo') == 'on',
    }


def aviso_para_form_data(aviso):
    expira_em = ''

    if aviso.expira_em:
        expira_em = timezone.localtime(aviso.expira_em).strftime('%Y-%m-%dT%H:%M')

    return {
        'titulo': aviso.titulo,
        'tipo': aviso.tipo,
        'prioridade': aviso.prioridade,
        'unidade': str(aviso.unidade_id) if aviso.unidade_id else '',
        'unidades_compartilhadas': [
            str(unidade.id) for unidade in aviso.unidades_compartilhadas.all()
        ],
        'grupos_permitidos': [
            str(grupo.id) for grupo in aviso.grupos_permitidos.all()
        ],
        'resumo': aviso.resumo,
        'mensagem': aviso.mensagem,
        'link_externo': aviso.link_externo,
        'expira_em': expira_em,
        'fixar_no_topo': aviso.fixar_no_topo,
        'exibir_no_dashboard': aviso.exibir_no_dashboard,
        'ativo': aviso.ativo,
        'remover_arquivo': False,
    }


def converter_expira_em(expira_em_texto):
    if not expira_em_texto:
        return None, ''

    try:
        expira_em = timezone.datetime.fromisoformat(expira_em_texto)

        if timezone.is_naive(expira_em):
            expira_em = timezone.make_aware(expira_em)

        return expira_em, ''
    except ValueError:
        return None, 'Data de expiração inválida.'


def buscar_dados_formulario():
    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    grupos = Group.objects.all().order_by(
        'name'
    )

    return unidades, grupos


def validar_formulario_aviso(form_data):
    erros = []

    if not form_data['titulo']:
        erros.append('Informe o título do aviso.')

    if not form_data['tipo']:
        erros.append('Informe o tipo do aviso.')

    if not form_data['prioridade']:
        erros.append('Informe a prioridade do aviso.')

    if not form_data['mensagem']:
        erros.append('Informe a mensagem do aviso.')

    if not form_data['unidade'] and form_data['unidades_compartilhadas']:
        erros.append(
            'Para compartilhar entre unidades específicas, selecione uma unidade principal. '
            'Se deixar a unidade em branco, o aviso será geral para todas as unidades.'
        )

    return erros


@login_required(login_url='/')
def avisos_comunicados(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_AVISOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if usuario_pode_gerenciar_avisos(request.user):
        avisos = buscar_avisos_para_gestao(request.user)
    else:
        avisos = buscar_avisos_visiveis(request.user)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    prioridade = request.GET.get('prioridade', '').strip()
    status = request.GET.get('status', '').strip()

    if busca:
        avisos = avisos.filter(
            Q(titulo__icontains=busca) |
            Q(resumo__icontains=busca) |
            Q(mensagem__icontains=busca) |
            Q(link_externo__icontains=busca)
        )

    if unidade_id:
        if unidade_id == 'geral':
            avisos = avisos.filter(unidade__isnull=True)
        else:
            avisos = avisos.filter(
                Q(unidade_id=unidade_id) |
                Q(unidades_compartilhadas__id=unidade_id)
            ).distinct()

    if tipo:
        avisos = avisos.filter(tipo=tipo)

    if prioridade:
        avisos = avisos.filter(prioridade=prioridade)

    if status == 'ativo':
        avisos = avisos.filter(ativo=True)
    elif status == 'inativo':
        avisos = avisos.filter(ativo=False)
    elif status == 'expirado':
        avisos = avisos.filter(expira_em__isnull=False, expira_em__lt=timezone.now())

    if usuario_eh_admin_ti(request.user):
        unidades = Unidade.objects.filter(ativo=True).order_by('nome')
    else:
        unidades = Unidade.objects.filter(id=request.user.unidade_id, ativo=True).order_by('nome')

    total_avisos = avisos.count()
    total_ativos = avisos.filter(ativo=True).count()
    total_inativos = avisos.filter(ativo=False).count()
    total_gerais = avisos.filter(unidade__isnull=True).count()
    total_expirados = avisos.filter(
        expira_em__isnull=False,
        expira_em__lt=timezone.now()
    ).count()

    return render(request, 'avisos/avisos_comunicados.html', {
        'avisos': avisos,
        'unidades': unidades,
        'tipos': AvisoComunicado.TIPO_CHOICES,
        'prioridades': AvisoComunicado.PRIORIDADE_CHOICES,
        'busca': busca,
        'unidade_id': unidade_id,
        'tipo': tipo,
        'prioridade': prioridade,
        'status': status,
        'total_avisos': total_avisos,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'total_gerais': total_gerais,
        'total_expirados': total_expirados,
        'pode_gerenciar_avisos': usuario_pode_gerenciar_avisos(request.user),
        'usuario_eh_admin_ti': usuario_eh_admin_ti(request.user),
    })


@login_required(login_url='/')
def novo_aviso_comunicado(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_AVISOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_avisos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    unidades, grupos = buscar_dados_formulario()

    form_data = {
        'titulo': '',
        'tipo': 'comunicado',
        'prioridade': 'normal',
        'unidade': '',
        'unidades_compartilhadas': [],
        'grupos_permitidos': [],
        'resumo': '',
        'mensagem': '',
        'link_externo': '',
        'expira_em': '',
        'fixar_no_topo': False,
        'exibir_no_dashboard': True,
        'ativo': True,
        'remover_arquivo': False,
    }

    erro = ''

    if request.method == 'POST':
        form_data = montar_form_data_aviso(request)
        arquivo = request.FILES.get('arquivo')

        erros = validar_formulario_aviso(form_data)

        expira_em, erro_data = converter_expira_em(form_data['expira_em'])

        if erro_data:
            erros.append(erro_data)

        if erros:
            erro = ' '.join(erros)
        else:
            unidade = None

            if form_data['unidade']:
                unidade = get_object_or_404(
                    Unidade,
                    id=form_data['unidade'],
                    ativo=True
                )

            with transaction.atomic():
                aviso = AvisoComunicado.objects.create(
                    titulo=form_data['titulo'],
                    tipo=form_data['tipo'],
                    prioridade=form_data['prioridade'],
                    resumo=form_data['resumo'],
                    mensagem=form_data['mensagem'],
                    unidade=unidade,
                    link_externo=form_data['link_externo'],
                    arquivo=arquivo,
                    fixar_no_topo=form_data['fixar_no_topo'],
                    exibir_no_dashboard=form_data['exibir_no_dashboard'],
                    ativo=form_data['ativo'],
                    publicado_em=timezone.now(),
                    expira_em=expira_em,
                    criado_por=request.user,
                )

                aviso.unidades_compartilhadas.set(form_data['unidades_compartilhadas'])
                aviso.grupos_permitidos.set(form_data['grupos_permitidos'])

                registrar_auditoria_aviso(
                    request,
                    aviso,
                    'criado',
                    f'Aviso criado: {aviso.titulo}'
                )

            return redirect('avisos_comunicados')

    return render(request, 'avisos/novo_aviso_comunicado.html', {
        'titulo_pagina': 'Novo aviso / comunicado',
        'subtitulo_pagina': 'Publique comunicados internos, manutenções, mudanças de fluxo e orientações para os usuários.',
        'botao_salvar': 'Publicar aviso',
        'modo': 'novo',
        'url_salvar': '/portal/modulos/avisos/novo/',
        'aviso': None,
        'form_data': form_data,
        'unidades': unidades,
        'grupos': grupos,
        'tipos': AvisoComunicado.TIPO_CHOICES,
        'prioridades': AvisoComunicado.PRIORIDADE_CHOICES,
        'erro': erro,
    })


@login_required(login_url='/')
def editar_aviso_comunicado(request, aviso_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_AVISOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_avisos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    aviso = get_object_or_404(
        AvisoComunicado.objects.prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ),
        id=aviso_id
    )

    unidades, grupos = buscar_dados_formulario()
    form_data = aviso_para_form_data(aviso)
    erro = ''

    if request.method == 'POST':
        form_data = montar_form_data_aviso(request)
        arquivo = request.FILES.get('arquivo')

        erros = validar_formulario_aviso(form_data)

        expira_em, erro_data = converter_expira_em(form_data['expira_em'])

        if erro_data:
            erros.append(erro_data)

        if erros:
            erro = ' '.join(erros)
        else:
            unidade = None

            if form_data['unidade']:
                unidade = get_object_or_404(
                    Unidade,
                    id=form_data['unidade'],
                    ativo=True
                )

            with transaction.atomic():
                aviso.titulo = form_data['titulo']
                aviso.tipo = form_data['tipo']
                aviso.prioridade = form_data['prioridade']
                aviso.resumo = form_data['resumo']
                aviso.mensagem = form_data['mensagem']
                aviso.unidade = unidade
                aviso.link_externo = form_data['link_externo']
                aviso.fixar_no_topo = form_data['fixar_no_topo']
                aviso.exibir_no_dashboard = form_data['exibir_no_dashboard']
                aviso.ativo = form_data['ativo']
                aviso.expira_em = expira_em

                if form_data['remover_arquivo']:
                    aviso.arquivo = None

                if arquivo:
                    aviso.arquivo = arquivo

                aviso.save()

                aviso.unidades_compartilhadas.set(form_data['unidades_compartilhadas'])
                aviso.grupos_permitidos.set(form_data['grupos_permitidos'])

                registrar_auditoria_aviso(
                    request,
                    aviso,
                    'alterado',
                    f'Aviso alterado: {aviso.titulo}'
                )

            return redirect('avisos_comunicados')

    return render(request, 'avisos/novo_aviso_comunicado.html', {
        'titulo_pagina': 'Editar aviso / comunicado',
        'subtitulo_pagina': 'Atualize as informações, permissões, unidade, grupos e validade do comunicado.',
        'botao_salvar': 'Salvar alterações',
        'modo': 'editar',
        'url_salvar': f'/portal/modulos/avisos/editar/{aviso.id}/',
        'aviso': aviso,
        'form_data': form_data,
        'unidades': unidades,
        'grupos': grupos,
        'tipos': AvisoComunicado.TIPO_CHOICES,
        'prioridades': AvisoComunicado.PRIORIDADE_CHOICES,
        'erro': erro,
    })


@login_required(login_url='/')
def inativar_aviso_comunicado(request, aviso_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_AVISOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_avisos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    aviso = get_object_or_404(
        AvisoComunicado.objects.prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ),
        id=aviso_id
    )

    if request.method == 'POST':
        aviso.ativo = False
        aviso.save()

        registrar_auditoria_aviso(
            request,
            aviso,
            'alterado',
            f'Aviso inativado: {aviso.titulo}'
        )

    return redirect('avisos_comunicados')


@login_required(login_url='/')
def reativar_aviso_comunicado(request, aviso_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_AVISOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_avisos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    aviso = get_object_or_404(
        AvisoComunicado.objects.prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ),
        id=aviso_id
    )

    if request.method == 'POST':
        aviso.ativo = True
        aviso.save()

        registrar_auditoria_aviso(
            request,
            aviso,
            'alterado',
            f'Aviso reativado: {aviso.titulo}'
        )

    return redirect('avisos_comunicados')