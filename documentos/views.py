from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from modulos.models import Modulo
from usuarios.models import Unidade, Setor
from .models import DocumentoProtocolo


NOME_MODULO_DOCUMENTOS = 'Documentos / Protocolos ONA'


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


def usuario_eh_admin_ti(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def usuario_pode_gerenciar_documentos(user):
    if user.is_superuser:
        return True

    if user.groups.filter(name='TI Administrador').exists():
        return True

    if user.groups.filter(name='Qualidade').exists():
        return True

    return False


def obter_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def registrar_auditoria_documento(request, documento, acao, titulo):
    unidades_compartilhadas = ', '.join(
        documento.unidades_compartilhadas.values_list('sigla', flat=True)
    ) or 'Nenhuma'

    grupos = ', '.join(
        documento.grupos_permitidos.values_list('name', flat=True)
    ) or 'Todos os grupos com acesso ao módulo'

    RegistroAuditoria.objects.create(
        modulo='documentos',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Código: {documento.codigo or "Não informado"}\n'
            f'Título: {documento.titulo}\n'
            f'Tipo: {documento.get_tipo_display()}\n'
            f'Categoria: {documento.get_categoria_display()}\n'
            f'Status: {documento.get_status_display()}\n'
            f'Unidade principal: {documento.unidade.nome if documento.unidade else "Geral / Todas as unidades"}\n'
            f'Unidades compartilhadas: {unidades_compartilhadas}\n'
            f'Setor: {documento.setor.nome if documento.setor else "Todos / Não informado"}\n'
            f'Grupos permitidos: {grupos}\n'
            f'Versão: {documento.versao or "Não informada"}\n'
            f'Responsável: {documento.responsavel or "Não informado"}\n'
            f'Data de publicação: {documento.data_publicacao.strftime("%d/%m/%Y") if documento.data_publicacao else "Não informada"}\n'
            f'Data de validade: {documento.data_validade.strftime("%d/%m/%Y") if documento.data_validade else "Não informada"}\n'
            f'Exibir no dashboard: {"Sim" if documento.exibir_no_dashboard else "Não"}\n'
            f'Leitura obrigatória: {"Sim" if documento.leitura_obrigatoria else "Não"}\n'
            f'Ativo: {"Sim" if documento.ativo else "Não"}'
        ),
        modelo='DocumentoProtocolo',
        objeto_id=str(documento.id),
        usuario=request.user,
        unidade=documento.unidade,
        ip_origem=obter_ip_cliente(request),
    )


def buscar_documentos_visiveis(user):
    documentos = DocumentoProtocolo.objects.filter(
        ativo=True
    ).exclude(
        status='inativo'
    )

    if usuario_eh_admin_ti(user):
        return documentos.select_related(
            'unidade',
            'setor',
            'criado_por'
        ).prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ).order_by(
            'categoria',
            'tipo',
            'titulo'
        )

    documentos = documentos.filter(
        Q(unidade=user.unidade) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=user.unidade)
    ).filter(
        Q(setor=user.setor) |
        Q(setor__isnull=True)
    )

    grupos_usuario = user.groups.all()

    return documentos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().select_related(
        'unidade',
        'setor',
        'criado_por'
    ).prefetch_related(
        'grupos_permitidos',
        'unidades_compartilhadas'
    ).order_by(
        'categoria',
        'tipo',
        'titulo'
    )


def buscar_documentos_para_gestao(user):
    documentos = DocumentoProtocolo.objects.all()

    if usuario_eh_admin_ti(user):
        return documentos.select_related(
            'unidade',
            'setor',
            'criado_por'
        ).prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ).order_by(
            '-ativo',
            'categoria',
            'tipo',
            'titulo'
        )

    return documentos.filter(
        Q(unidade=user.unidade) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=user.unidade)
    ).distinct().select_related(
        'unidade',
        'setor',
        'criado_por'
    ).prefetch_related(
        'grupos_permitidos',
        'unidades_compartilhadas'
    ).order_by(
        '-ativo',
        'categoria',
        'tipo',
        'titulo'
    )


def buscar_dados_formulario():
    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    setores = Setor.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    grupos = Group.objects.all().order_by(
        'name'
    )

    return unidades, setores, grupos


def montar_form_data_documento(request):
    return {
        'codigo': request.POST.get('codigo', '').strip(),
        'titulo': request.POST.get('titulo', '').strip(),
        'tipo': request.POST.get('tipo', '').strip(),
        'categoria': request.POST.get('categoria', '').strip(),
        'unidade': request.POST.get('unidade', '').strip(),
        'unidades_compartilhadas': request.POST.getlist('unidades_compartilhadas'),
        'setor': request.POST.get('setor', '').strip(),
        'grupos_permitidos': request.POST.getlist('grupos_permitidos'),
        'descricao': request.POST.get('descricao', '').strip(),
        'versao': request.POST.get('versao', '').strip(),
        'responsavel': request.POST.get('responsavel', '').strip(),
        'data_publicacao': request.POST.get('data_publicacao', '').strip(),
        'data_validade': request.POST.get('data_validade', '').strip(),
        'status': request.POST.get('status', '').strip(),
        'exibir_no_dashboard': request.POST.get('exibir_no_dashboard') == 'on',
        'leitura_obrigatoria': request.POST.get('leitura_obrigatoria') == 'on',
        'ativo': request.POST.get('ativo') == 'on',
        'remover_arquivo': request.POST.get('remover_arquivo') == 'on',
    }


def documento_para_form_data(documento):
    data_publicacao = ''

    if documento.data_publicacao:
        data_publicacao = documento.data_publicacao.strftime('%Y-%m-%d')

    data_validade = ''

    if documento.data_validade:
        data_validade = documento.data_validade.strftime('%Y-%m-%d')

    return {
        'codigo': documento.codigo,
        'titulo': documento.titulo,
        'tipo': documento.tipo,
        'categoria': documento.categoria,
        'unidade': str(documento.unidade_id) if documento.unidade_id else '',
        'unidades_compartilhadas': [
            str(unidade.id) for unidade in documento.unidades_compartilhadas.all()
        ],
        'setor': str(documento.setor_id) if documento.setor_id else '',
        'grupos_permitidos': [
            str(grupo.id) for grupo in documento.grupos_permitidos.all()
        ],
        'descricao': documento.descricao,
        'versao': documento.versao,
        'responsavel': documento.responsavel,
        'data_publicacao': data_publicacao,
        'data_validade': data_validade,
        'status': documento.status,
        'exibir_no_dashboard': documento.exibir_no_dashboard,
        'leitura_obrigatoria': documento.leitura_obrigatoria,
        'ativo': documento.ativo,
        'remover_arquivo': False,
    }


def converter_data(data_texto, nome_campo):
    if not data_texto:
        return None, ''

    try:
        return timezone.datetime.strptime(
            data_texto,
            '%Y-%m-%d'
        ).date(), ''
    except ValueError:
        return None, f'{nome_campo} inválida.'


def validar_formulario_documento(form_data, arquivo, modo):
    erros = []

    if not form_data['titulo']:
        erros.append('Informe o título do documento.')

    if not form_data['tipo']:
        erros.append('Informe o tipo do documento.')

    if not form_data['categoria']:
        erros.append('Informe a categoria do documento.')

    if not form_data['status']:
        erros.append('Informe o status do documento.')

    if modo == 'novo' and not arquivo:
        erros.append('Selecione o arquivo do documento.')

    if not form_data['unidade'] and form_data['unidades_compartilhadas']:
        erros.append(
            'Para compartilhar entre unidades específicas, selecione uma unidade principal. '
            'Se deixar a unidade em branco, o documento será geral para todas as unidades.'
        )

    return erros


@login_required(login_url='/')
def documentos_protocolos(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_DOCUMENTOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if usuario_pode_gerenciar_documentos(request.user):
        documentos = buscar_documentos_para_gestao(request.user)
    else:
        documentos = buscar_documentos_visiveis(request.user)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    setor_id = request.GET.get('setor', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    status = request.GET.get('status', '').strip()
    vencimento = request.GET.get('vencimento', '').strip()
    ativo = request.GET.get('ativo', '').strip()

    hoje = timezone.localdate()
    limite_30_dias = hoje + timezone.timedelta(days=30)

    if busca:
        documentos = documentos.filter(
            Q(codigo__icontains=busca) |
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(responsavel__icontains=busca)
        )

    if unidade_id:
        if unidade_id == 'geral':
            documentos = documentos.filter(unidade__isnull=True)
        else:
            documentos = documentos.filter(
                Q(unidade_id=unidade_id) |
                Q(unidades_compartilhadas__id=unidade_id)
            ).distinct()

    if setor_id:
        documentos = documentos.filter(setor_id=setor_id)

    if tipo:
        documentos = documentos.filter(tipo=tipo)

    if categoria:
        documentos = documentos.filter(categoria=categoria)

    if status:
        documentos = documentos.filter(status=status)

    if ativo == 'ativo':
        documentos = documentos.filter(ativo=True)
    elif ativo == 'inativo':
        documentos = documentos.filter(ativo=False)

    if vencimento == 'vencidos':
        documentos = documentos.filter(
            data_validade__isnull=False,
            data_validade__lt=hoje
        )

    if vencimento == 'proximos':
        documentos = documentos.filter(
            data_validade__isnull=False,
            data_validade__gte=hoje,
            data_validade__lte=limite_30_dias
        )

    if vencimento == 'sem_validade':
        documentos = documentos.filter(
            data_validade__isnull=True
        )

    total_documentos = documentos.count()

    documentos_base = buscar_documentos_visiveis(request.user)

    if usuario_pode_gerenciar_documentos(request.user):
        documentos_base = buscar_documentos_para_gestao(request.user)

    total_vencidos = documentos_base.filter(
        data_validade__isnull=False,
        data_validade__lt=hoje
    ).count()

    total_proximos = documentos_base.filter(
        data_validade__isnull=False,
        data_validade__gte=hoje,
        data_validade__lte=limite_30_dias
    ).count()

    total_ativos = documentos_base.filter(ativo=True).count()
    total_inativos = documentos_base.filter(ativo=False).count()
    total_gerais = documentos_base.filter(unidade__isnull=True).count()
    total_em_revisao = documentos_base.filter(status='em_revisao').count()

    if usuario_eh_admin_ti(request.user):
        unidades = Unidade.objects.filter(ativo=True).order_by('nome')
    else:
        unidades = Unidade.objects.filter(id=request.user.unidade_id, ativo=True).order_by('nome')

    setores = Setor.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    return render(request, 'documentos/documentos_protocolos.html', {
        'documentos': documentos,
        'unidades': unidades,
        'setores': setores,
        'tipos': DocumentoProtocolo.TIPO_CHOICES,
        'categorias': DocumentoProtocolo.CATEGORIA_CHOICES,
        'status_choices': DocumentoProtocolo.STATUS_CHOICES,
        'busca': busca,
        'unidade_id': unidade_id,
        'setor_id': setor_id,
        'tipo': tipo,
        'categoria': categoria,
        'status': status,
        'vencimento': vencimento,
        'ativo': ativo,
        'total_documentos': total_documentos,
        'total_vencidos': total_vencidos,
        'total_proximos': total_proximos,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'total_gerais': total_gerais,
        'total_em_revisao': total_em_revisao,
        'pode_gerenciar_documentos': usuario_pode_gerenciar_documentos(request.user),
        'usuario_eh_admin_ti': usuario_eh_admin_ti(request.user),
    })


@login_required(login_url='/')
def novo_documento_protocolo(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_DOCUMENTOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_documentos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    unidades, setores, grupos = buscar_dados_formulario()

    form_data = {
        'codigo': '',
        'titulo': '',
        'tipo': 'pop',
        'categoria': 'assistencial',
        'unidade': '',
        'unidades_compartilhadas': [],
        'setor': '',
        'grupos_permitidos': [],
        'descricao': '',
        'versao': '',
        'responsavel': '',
        'data_publicacao': timezone.localdate().strftime('%Y-%m-%d'),
        'data_validade': '',
        'status': 'vigente',
        'exibir_no_dashboard': False,
        'leitura_obrigatoria': False,
        'ativo': True,
        'remover_arquivo': False,
    }

    erro = ''

    if request.method == 'POST':
        form_data = montar_form_data_documento(request)
        arquivo = request.FILES.get('arquivo')

        erros = validar_formulario_documento(form_data, arquivo, 'novo')

        data_publicacao, erro_publicacao = converter_data(
            form_data['data_publicacao'],
            'Data de publicação'
        )

        if erro_publicacao:
            erros.append(erro_publicacao)

        if not data_publicacao:
            data_publicacao = timezone.localdate()

        data_validade, erro_validade = converter_data(
            form_data['data_validade'],
            'Data de validade'
        )

        if erro_validade:
            erros.append(erro_validade)

        if erros:
            erro = ' '.join(erros)
        else:
            unidade = None
            setor = None

            if form_data['unidade']:
                unidade = get_object_or_404(
                    Unidade,
                    id=form_data['unidade'],
                    ativo=True
                )

            if form_data['setor']:
                setor = get_object_or_404(
                    Setor,
                    id=form_data['setor'],
                    ativo=True
                )

            with transaction.atomic():
                documento = DocumentoProtocolo.objects.create(
                    codigo=form_data['codigo'],
                    titulo=form_data['titulo'],
                    tipo=form_data['tipo'],
                    categoria=form_data['categoria'],
                    unidade=unidade,
                    setor=setor,
                    descricao=form_data['descricao'],
                    arquivo=arquivo,
                    versao=form_data['versao'],
                    responsavel=form_data['responsavel'],
                    data_publicacao=data_publicacao,
                    data_validade=data_validade,
                    status=form_data['status'],
                    exibir_no_dashboard=form_data['exibir_no_dashboard'],
                    leitura_obrigatoria=form_data['leitura_obrigatoria'],
                    ativo=form_data['ativo'],
                    criado_por=request.user,
                )

                documento.unidades_compartilhadas.set(form_data['unidades_compartilhadas'])
                documento.grupos_permitidos.set(form_data['grupos_permitidos'])

                registrar_auditoria_documento(
                    request,
                    documento,
                    'criado',
                    f'Documento criado: {documento.titulo}'
                )

            return redirect('documentos_protocolos')

    return render(request, 'documentos/novo_documento_protocolo.html', {
        'titulo_pagina': 'Novo documento / protocolo',
        'subtitulo_pagina': 'Cadastre POPs, protocolos, políticas internas, fluxos e documentos institucionais.',
        'botao_salvar': 'Cadastrar documento',
        'modo': 'novo',
        'url_salvar': '/portal/modulos/documentos/novo/',
        'documento': None,
        'form_data': form_data,
        'unidades': unidades,
        'setores': setores,
        'grupos': grupos,
        'tipos': DocumentoProtocolo.TIPO_CHOICES,
        'categorias': DocumentoProtocolo.CATEGORIA_CHOICES,
        'status_choices': DocumentoProtocolo.STATUS_CHOICES,
        'erro': erro,
    })


@login_required(login_url='/')
def editar_documento_protocolo(request, documento_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_DOCUMENTOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_documentos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    documento = get_object_or_404(
        DocumentoProtocolo.objects.prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ),
        id=documento_id
    )

    unidades, setores, grupos = buscar_dados_formulario()
    form_data = documento_para_form_data(documento)
    erro = ''

    if request.method == 'POST':
        form_data = montar_form_data_documento(request)
        arquivo = request.FILES.get('arquivo')

        erros = validar_formulario_documento(form_data, arquivo, 'editar')

        data_publicacao, erro_publicacao = converter_data(
            form_data['data_publicacao'],
            'Data de publicação'
        )

        if erro_publicacao:
            erros.append(erro_publicacao)

        if not data_publicacao:
            data_publicacao = timezone.localdate()

        data_validade, erro_validade = converter_data(
            form_data['data_validade'],
            'Data de validade'
        )

        if erro_validade:
            erros.append(erro_validade)

        if erros:
            erro = ' '.join(erros)
        else:
            unidade = None
            setor = None

            if form_data['unidade']:
                unidade = get_object_or_404(
                    Unidade,
                    id=form_data['unidade'],
                    ativo=True
                )

            if form_data['setor']:
                setor = get_object_or_404(
                    Setor,
                    id=form_data['setor'],
                    ativo=True
                )

            with transaction.atomic():
                documento.codigo = form_data['codigo']
                documento.titulo = form_data['titulo']
                documento.tipo = form_data['tipo']
                documento.categoria = form_data['categoria']
                documento.unidade = unidade
                documento.setor = setor
                documento.descricao = form_data['descricao']
                documento.versao = form_data['versao']
                documento.responsavel = form_data['responsavel']
                documento.data_publicacao = data_publicacao
                documento.data_validade = data_validade
                documento.status = form_data['status']
                documento.exibir_no_dashboard = form_data['exibir_no_dashboard']
                documento.leitura_obrigatoria = form_data['leitura_obrigatoria']
                documento.ativo = form_data['ativo']

                if form_data['remover_arquivo']:
                    documento.arquivo = None

                if arquivo:
                    documento.arquivo = arquivo

                documento.save()

                documento.unidades_compartilhadas.set(form_data['unidades_compartilhadas'])
                documento.grupos_permitidos.set(form_data['grupos_permitidos'])

                registrar_auditoria_documento(
                    request,
                    documento,
                    'alterado',
                    f'Documento alterado: {documento.titulo}'
                )

            return redirect('documentos_protocolos')

    return render(request, 'documentos/novo_documento_protocolo.html', {
        'titulo_pagina': 'Editar documento / protocolo',
        'subtitulo_pagina': 'Atualize as informações, permissões, unidade, grupos, validade e arquivo do documento.',
        'botao_salvar': 'Salvar alterações',
        'modo': 'editar',
        'url_salvar': f'/portal/modulos/documentos/editar/{documento.id}/',
        'documento': documento,
        'form_data': form_data,
        'unidades': unidades,
        'setores': setores,
        'grupos': grupos,
        'tipos': DocumentoProtocolo.TIPO_CHOICES,
        'categorias': DocumentoProtocolo.CATEGORIA_CHOICES,
        'status_choices': DocumentoProtocolo.STATUS_CHOICES,
        'erro': erro,
    })


@login_required(login_url='/')
def inativar_documento_protocolo(request, documento_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_DOCUMENTOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_documentos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    documento = get_object_or_404(
        DocumentoProtocolo.objects.prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ),
        id=documento_id
    )

    if request.method == 'POST':
        documento.ativo = False
        documento.status = 'inativo'
        documento.save()

        registrar_auditoria_documento(
            request,
            documento,
            'alterado',
            f'Documento inativado: {documento.titulo}'
        )

    return redirect('documentos_protocolos')


@login_required(login_url='/')
def reativar_documento_protocolo(request, documento_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_DOCUMENTOS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_documentos(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    documento = get_object_or_404(
        DocumentoProtocolo.objects.prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ),
        id=documento_id
    )

    if request.method == 'POST':
        documento.ativo = True

        if documento.status == 'inativo':
            documento.status = 'vigente'

        documento.save()

        registrar_auditoria_documento(
            request,
            documento,
            'alterado',
            f'Documento reativado: {documento.titulo}'
        )

    return redirect('documentos_protocolos')