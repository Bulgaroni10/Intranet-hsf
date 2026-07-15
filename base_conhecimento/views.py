import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from usuarios.models import Unidade, Setor
from usuarios.escopo import aplicar_escopo_unidade

from .models import (
    CategoriaConhecimento,
    DocumentoConhecimento,
    LeituraDocumentoConhecimento,
)


def usuario_eh_admin_ti(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def obter_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def registrar_auditoria_base(request, acao, titulo, descricao, modelo='', objeto_id=''):
    RegistroAuditoria.objects.create(
        modulo='conteudos',
        acao=acao,
        titulo=titulo,
        descricao=descricao,
        modelo=modelo,
        objeto_id=str(objeto_id) if objeto_id else '',
        usuario=request.user,
        unidade=getattr(request.user, 'unidade', None),
        ip_origem=obter_ip_cliente(request),
    )


def buscar_documentos_visiveis(request):
    user = request.user
    unidade_usuario = getattr(user, 'unidade', None)
    setor_usuario = getattr(user, 'setor', None)

    documentos = aplicar_escopo_unidade(DocumentoConhecimento.objects.select_related(
        'categoria',
        'unidade',
        'setor',
        'responsavel_revisao',
        'criado_por',
        'atualizado_por',
    ).prefetch_related(
        'grupos_permitidos'
    ), user, incluir_globais=True)

    if not usuario_eh_admin_ti(user):
        documentos = documentos.filter(
            ativo=True
        ).filter(
            Q(setor=setor_usuario) |
            Q(setor__isnull=True)
        )

        grupos_usuario = user.groups.all()

        documentos = documentos.filter(
            Q(grupos_permitidos__in=grupos_usuario) |
            Q(grupos_permitidos__isnull=True)
        ).distinct()

    busca = request.GET.get('busca', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    setor_id = request.GET.get('setor', '').strip()
    status = request.GET.get('status', '').strip()
    leitura_obrigatoria = request.GET.get('leitura_obrigatoria', '').strip()
    ativo = request.GET.get('ativo', '').strip()

    if busca:
        documentos = documentos.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(versao__icontains=busca) |
            Q(link_externo__icontains=busca) |
            Q(categoria__nome__icontains=busca) |
            Q(unidade__nome__icontains=busca) |
            Q(unidade__sigla__icontains=busca) |
            Q(setor__nome__icontains=busca)
        )

    if categoria_id:
        documentos = documentos.filter(categoria_id=categoria_id)

    if tipo:
        documentos = documentos.filter(tipo=tipo)

    if unidade_id:
        if unidade_id == 'geral':
            documentos = documentos.filter(unidade__isnull=True)
        else:
            documentos = documentos.filter(unidade_id=unidade_id)

    if setor_id:
        if setor_id == 'geral':
            documentos = documentos.filter(setor__isnull=True)
        else:
            documentos = documentos.filter(setor_id=setor_id)

    if status:
        documentos = documentos.filter(status=status)

    if leitura_obrigatoria == 'sim':
        documentos = documentos.filter(leitura_obrigatoria=True)

    if leitura_obrigatoria == 'nao':
        documentos = documentos.filter(leitura_obrigatoria=False)

    if usuario_eh_admin_ti(user):
        if ativo == 'sim':
            documentos = documentos.filter(ativo=True)

        elif ativo == 'nao':
            documentos = documentos.filter(ativo=False)

    return documentos.order_by(
        'ordem',
        'categoria__nome',
        'setor__nome',
        'titulo',
    )


@login_required(login_url='/')
def base_conhecimento(request):
    documentos_queryset = buscar_documentos_visiveis(request)

    categorias = CategoriaConhecimento.objects.filter(
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

    setores = Setor.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    total_documentos = documentos_queryset.count()
    total_vigentes = documentos_queryset.filter(status='vigente').count()
    total_revisao = documentos_queryset.filter(status='em_revisao').count()
    total_obsoletos = documentos_queryset.filter(status='obsoleto').count()
    total_leitura_obrigatoria = documentos_queryset.filter(leitura_obrigatoria=True).count()

    documentos = list(documentos_queryset)

    leituras_usuario = list(
        LeituraDocumentoConhecimento.objects.filter(
            usuario=request.user,
            documento__in=documentos,
        ).values(
            'documento_id',
            'versao_documento',
        )
    )

    documentos_lidos_ids = []

    for documento in documentos:
        for leitura in leituras_usuario:
            if leitura['documento_id'] == documento.id and leitura['versao_documento'] == documento.versao:
                documentos_lidos_ids.append(documento.id)

    total_pendentes_leitura = 0

    for documento in documentos:
        if documento.leitura_obrigatoria and documento.ativo and documento.id not in documentos_lidos_ids:
            total_pendentes_leitura += 1

    return render(request, 'base_conhecimento/base_conhecimento.html', {
        'documentos': documentos,
        'documentos_lidos_ids': documentos_lidos_ids,

        'categorias': categorias,
        'unidades': unidades,
        'setores': setores,
        'tipos': DocumentoConhecimento.TIPO_CHOICES,
        'status_choices': DocumentoConhecimento.STATUS_CHOICES,

        'busca': request.GET.get('busca', '').strip(),
        'categoria_id': request.GET.get('categoria', '').strip(),
        'tipo_selecionado': request.GET.get('tipo', '').strip(),
        'unidade_id': request.GET.get('unidade', '').strip(),
        'setor_id': request.GET.get('setor', '').strip(),
        'status_selecionado': request.GET.get('status', '').strip(),
        'leitura_obrigatoria': request.GET.get('leitura_obrigatoria', '').strip(),
        'ativo_selecionado': request.GET.get('ativo', '').strip(),

        'total_documentos': total_documentos,
        'total_vigentes': total_vigentes,
        'total_revisao': total_revisao,
        'total_obsoletos': total_obsoletos,
        'total_leitura_obrigatoria': total_leitura_obrigatoria,
        'total_pendentes_leitura': total_pendentes_leitura,

        'pode_gerenciar': usuario_eh_admin_ti(request.user),
    })


@login_required(login_url='/')
def confirmar_leitura_documento(request, documento_id):
    documento = get_object_or_404(
        DocumentoConhecimento,
        id=documento_id,
        ativo=True,
        leitura_obrigatoria=True,
    )

    documento_visivel = buscar_documentos_visiveis(request).filter(
        id=documento.id
    ).exists()

    if not documento_visivel:
        return render(request, 'core/sem_permissao.html', status=403)

    LeituraDocumentoConhecimento.objects.get_or_create(
        documento=documento,
        usuario=request.user,
        versao_documento=documento.versao,
        defaults={
            'unidade_usuario': getattr(request.user, 'unidade', None),
            'setor_usuario': getattr(request.user, 'setor', None),
            'ip_origem': obter_ip_cliente(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    )

    registrar_auditoria_base(
        request=request,
        acao='criado',
        titulo=f'Leitura confirmada: {documento.titulo}',
        descricao=(
            f'O usuário confirmou ciência do documento obrigatório.\n'
            f'Documento: {documento.titulo}\n'
            f'Versão: {documento.versao}'
        ),
        modelo='LeituraDocumentoConhecimento',
        objeto_id=documento.id,
    )

    messages.success(request, 'Leitura confirmada com sucesso.')
    return redirect('/portal/modulos/base-conhecimento/')


def buscar_leituras_relatorio(request):
    leituras = LeituraDocumentoConhecimento.objects.select_related(
        'documento',
        'usuario',
        'unidade_usuario',
        'setor_usuario',
        'documento__categoria',
        'documento__unidade',
        'documento__setor',
    )

    documento_id = request.GET.get('documento', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    setor_id = request.GET.get('setor', '').strip()
    usuario_busca = request.GET.get('usuario', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    if documento_id:
        leituras = leituras.filter(documento_id=documento_id)

    if unidade_id:
        leituras = leituras.filter(unidade_usuario_id=unidade_id)

    if setor_id:
        leituras = leituras.filter(setor_usuario_id=setor_id)

    if usuario_busca:
        leituras = leituras.filter(
            Q(usuario__username__icontains=usuario_busca) |
            Q(usuario__first_name__icontains=usuario_busca) |
            Q(usuario__last_name__icontains=usuario_busca) |
            Q(usuario__email__icontains=usuario_busca)
        )

    if data_inicio:
        leituras = leituras.filter(confirmado_em__date__gte=data_inicio)

    if data_fim:
        leituras = leituras.filter(confirmado_em__date__lte=data_fim)

    return leituras.order_by('-confirmado_em')


@login_required(login_url='/')
def relatorio_leituras_conhecimento(request):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    leituras = buscar_leituras_relatorio(request)

    documentos = DocumentoConhecimento.objects.filter(
        leitura_obrigatoria=True
    ).order_by(
        'titulo',
        'versao'
    )

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

    total_leituras = leituras.count()
    total_documentos_obrigatorios = DocumentoConhecimento.objects.filter(
        ativo=True,
        leitura_obrigatoria=True
    ).count()

    return render(request, 'base_conhecimento/relatorio_leituras.html', {
        'leituras': leituras,
        'documentos': documentos,
        'unidades': unidades,
        'setores': setores,

        'documento_id': request.GET.get('documento', '').strip(),
        'unidade_id': request.GET.get('unidade', '').strip(),
        'setor_id': request.GET.get('setor', '').strip(),
        'usuario_busca': request.GET.get('usuario', '').strip(),
        'data_inicio': request.GET.get('data_inicio', '').strip(),
        'data_fim': request.GET.get('data_fim', '').strip(),

        'total_leituras': total_leituras,
        'total_documentos_obrigatorios': total_documentos_obrigatorios,
    })


@login_required(login_url='/')
def exportar_leituras_conhecimento_csv(request):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    leituras = buscar_leituras_relatorio(request)

    agora = timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="leituras_base_conhecimento_{agora}.csv"'

    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'Documento',
        'Versao',
        'Categoria',
        'Usuario',
        'Nome',
        'Email',
        'Unidade usuario',
        'Setor usuario',
        'Data confirmacao',
        'Hora confirmacao',
        'IP origem',
    ])

    for leitura in leituras:
        confirmado = timezone.localtime(leitura.confirmado_em)

        writer.writerow([
            leitura.documento.titulo,
            leitura.versao_documento,
            leitura.documento.categoria.nome if leitura.documento.categoria else '',
            leitura.usuario.username,
            leitura.usuario.get_full_name() or leitura.usuario.username,
            leitura.usuario.email,
            leitura.unidade_usuario.nome if leitura.unidade_usuario else '',
            leitura.setor_usuario.nome if leitura.setor_usuario else '',
            confirmado.strftime('%d/%m/%Y'),
            confirmado.strftime('%H:%M:%S'),
            leitura.ip_origem or '',
        ])

    return response


def montar_form_data_categoria(request):
    return {
        'nome': request.POST.get('nome', '').strip(),
        'descricao': request.POST.get('descricao', '').strip(),
        'ordem': request.POST.get('ordem', '0').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def categoria_para_form_data(categoria):
    return {
        'nome': categoria.nome,
        'descricao': categoria.descricao,
        'ordem': str(categoria.ordem),
        'ativo': categoria.ativo,
    }


def validar_categoria(form_data, categoria_id=None):
    erros = []

    if not form_data['nome']:
        erros.append('Informe o nome da categoria.')

    try:
        ordem = int(form_data['ordem'] or 0)

        if ordem < 0:
            erros.append('A ordem não pode ser negativa.')

    except ValueError:
        erros.append('A ordem precisa ser um número.')

    categoria_existente = CategoriaConhecimento.objects.filter(
        nome__iexact=form_data['nome']
    )

    if categoria_id:
        categoria_existente = categoria_existente.exclude(id=categoria_id)

    if form_data['nome'] and categoria_existente.exists():
        erros.append('Já existe uma categoria com este nome.')

    return erros


@login_required(login_url='/')
def nova_categoria_conhecimento(request):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'nome': '',
        'descricao': '',
        'ordem': '0',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_categoria(request)
        erros = validar_categoria(form_data)

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'base_conhecimento/formulario_categoria.html', {
                'modo': 'novo',
                'form_data': form_data,
            })

        categoria = CategoriaConhecimento.objects.create(
            nome=form_data['nome'],
            descricao=form_data['descricao'],
            ordem=int(form_data['ordem'] or 0),
            ativo=form_data['ativo'],
        )

        registrar_auditoria_base(
            request=request,
            acao='criado',
            titulo=f'Categoria criada: {categoria.nome}',
            descricao=f'Categoria criada na Base de Conhecimento: {categoria.nome}',
            modelo='CategoriaConhecimento',
            objeto_id=categoria.id,
        )

        messages.success(request, 'Categoria cadastrada com sucesso.')
        return redirect('/portal/modulos/base-conhecimento/')

    return render(request, 'base_conhecimento/formulario_categoria.html', {
        'modo': 'novo',
        'form_data': form_data,
    })


@login_required(login_url='/')
def editar_categoria_conhecimento(request, categoria_id):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    categoria = get_object_or_404(CategoriaConhecimento, id=categoria_id)
    form_data = categoria_para_form_data(categoria)

    if request.method == 'POST':
        form_data = montar_form_data_categoria(request)
        erros = validar_categoria(form_data, categoria_id=categoria.id)

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'base_conhecimento/formulario_categoria.html', {
                'modo': 'editar',
                'form_data': form_data,
                'categoria': categoria,
            })

        categoria.nome = form_data['nome']
        categoria.descricao = form_data['descricao']
        categoria.ordem = int(form_data['ordem'] or 0)
        categoria.ativo = form_data['ativo']
        categoria.save()

        registrar_auditoria_base(
            request=request,
            acao='alterado',
            titulo=f'Categoria alterada: {categoria.nome}',
            descricao=f'Categoria alterada na Base de Conhecimento: {categoria.nome}',
            modelo='CategoriaConhecimento',
            objeto_id=categoria.id,
        )

        messages.success(request, 'Categoria atualizada com sucesso.')
        return redirect('/portal/modulos/base-conhecimento/')

    return render(request, 'base_conhecimento/formulario_categoria.html', {
        'modo': 'editar',
        'form_data': form_data,
        'categoria': categoria,
    })


def montar_form_data_documento(request):
    return {
        'titulo': request.POST.get('titulo', '').strip(),
        'tipo': request.POST.get('tipo', 'pop').strip(),
        'categoria': request.POST.get('categoria', '').strip(),
        'unidade': request.POST.get('unidade', '').strip(),
        'setor': request.POST.get('setor', '').strip(),
        'descricao': request.POST.get('descricao', '').strip(),
        'link_externo': request.POST.get('link_externo', '').strip(),
        'versao': request.POST.get('versao', '1.0').strip(),
        'status': request.POST.get('status', 'vigente').strip(),
        'leitura_obrigatoria': request.POST.get('leitura_obrigatoria') == 'on',
        'responsavel_revisao': request.POST.get('responsavel_revisao', '').strip(),
        'data_revisao': request.POST.get('data_revisao', '').strip(),
        'ordem': request.POST.get('ordem', '0').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def documento_para_form_data(documento):
    return {
        'titulo': documento.titulo,
        'tipo': documento.tipo,
        'categoria': str(documento.categoria_id) if documento.categoria_id else '',
        'unidade': str(documento.unidade_id) if documento.unidade_id else '',
        'setor': str(documento.setor_id) if documento.setor_id else '',
        'descricao': documento.descricao,
        'link_externo': documento.link_externo,
        'versao': documento.versao,
        'status': documento.status,
        'leitura_obrigatoria': documento.leitura_obrigatoria,
        'responsavel_revisao': str(documento.responsavel_revisao_id) if documento.responsavel_revisao_id else '',
        'data_revisao': documento.data_revisao.strftime('%Y-%m-%d') if documento.data_revisao else '',
        'ordem': str(documento.ordem),
        'ativo': documento.ativo,
    }


def validar_documento(form_data):
    erros = []

    if not form_data['titulo']:
        erros.append('Informe o título do documento.')

    tipos_validos = [item[0] for item in DocumentoConhecimento.TIPO_CHOICES]

    if form_data['tipo'] not in tipos_validos:
        erros.append('Tipo inválido.')

    status_validos = [item[0] for item in DocumentoConhecimento.STATUS_CHOICES]

    if form_data['status'] not in status_validos:
        erros.append('Status inválido.')

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


def carregar_dados_form_documento():
    from django.contrib.auth import get_user_model

    Usuario = get_user_model()

    categorias = CategoriaConhecimento.objects.filter(
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

    setores = Setor.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    responsaveis = Usuario.objects.filter(
        is_active=True
    ).order_by(
        'first_name',
        'last_name',
        'username'
    )

    return categorias, unidades, setores, responsaveis


@login_required(login_url='/')
def novo_documento_conhecimento(request):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    categorias, unidades, setores, responsaveis = carregar_dados_form_documento()

    form_data = {
        'titulo': '',
        'tipo': 'pop',
        'categoria': '',
        'unidade': '',
        'setor': '',
        'descricao': '',
        'link_externo': '',
        'versao': '1.0',
        'status': 'vigente',
        'leitura_obrigatoria': False,
        'responsavel_revisao': '',
        'data_revisao': '',
        'ordem': '0',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_documento(request)
        erros = validar_documento(form_data)

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'base_conhecimento/formulario_documento.html', {
                'modo': 'novo',
                'form_data': form_data,
                'categorias': categorias,
                'unidades': unidades,
                'setores': setores,
                'responsaveis': responsaveis,
                'tipos': DocumentoConhecimento.TIPO_CHOICES,
                'status_choices': DocumentoConhecimento.STATUS_CHOICES,
            })

        categoria = None
        unidade = None
        setor = None
        responsavel = None

        if form_data['categoria']:
            categoria = get_object_or_404(CategoriaConhecimento, id=form_data['categoria'])

        if form_data['unidade']:
            unidade = get_object_or_404(Unidade, id=form_data['unidade'])

        if form_data['setor']:
            setor = get_object_or_404(Setor, id=form_data['setor'])

        if form_data['responsavel_revisao']:
            from django.contrib.auth import get_user_model
            Usuario = get_user_model()
            responsavel = get_object_or_404(Usuario, id=form_data['responsavel_revisao'])

        documento = DocumentoConhecimento.objects.create(
            titulo=form_data['titulo'],
            tipo=form_data['tipo'],
            categoria=categoria,
            unidade=unidade,
            setor=setor,
            descricao=form_data['descricao'],
            arquivo=request.FILES.get('arquivo'),
            link_externo=form_data['link_externo'],
            versao=form_data['versao'] or '1.0',
            status=form_data['status'],
            leitura_obrigatoria=form_data['leitura_obrigatoria'],
            responsavel_revisao=responsavel,
            data_revisao=form_data['data_revisao'] or None,
            ordem=int(form_data['ordem'] or 0),
            ativo=form_data['ativo'],
            criado_por=request.user,
            atualizado_por=request.user,
        )

        registrar_auditoria_base(
            request=request,
            acao='criado',
            titulo=f'Documento criado: {documento.titulo}',
            descricao=(
                f'Documento criado na Base de Conhecimento.\n'
                f'Título: {documento.titulo}\n'
                f'Tipo: {documento.get_tipo_display()}\n'
                f'Status: {documento.get_status_display()}\n'
                f'Destino: {documento.destino_exibicao}'
            ),
            modelo='DocumentoConhecimento',
            objeto_id=documento.id,
        )

        messages.success(request, 'Documento cadastrado com sucesso.')
        return redirect('/portal/modulos/base-conhecimento/')

    return render(request, 'base_conhecimento/formulario_documento.html', {
        'modo': 'novo',
        'form_data': form_data,
        'categorias': categorias,
        'unidades': unidades,
        'setores': setores,
        'responsaveis': responsaveis,
        'tipos': DocumentoConhecimento.TIPO_CHOICES,
        'status_choices': DocumentoConhecimento.STATUS_CHOICES,
    })


@login_required(login_url='/')
def editar_documento_conhecimento(request, documento_id):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    documento = get_object_or_404(
        aplicar_escopo_unidade(DocumentoConhecimento.objects.all(), request.user),
        id=documento_id,
    )
    categorias, unidades, setores, responsaveis = carregar_dados_form_documento()
    form_data = documento_para_form_data(documento)

    if request.method == 'POST':
        form_data = montar_form_data_documento(request)
        erros = validar_documento(form_data)

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'base_conhecimento/formulario_documento.html', {
                'modo': 'editar',
                'form_data': form_data,
                'documento': documento,
                'categorias': categorias,
                'unidades': unidades,
                'setores': setores,
                'responsaveis': responsaveis,
                'tipos': DocumentoConhecimento.TIPO_CHOICES,
                'status_choices': DocumentoConhecimento.STATUS_CHOICES,
            })

        categoria = None
        unidade = None
        setor = None
        responsavel = None

        if form_data['categoria']:
            categoria = get_object_or_404(CategoriaConhecimento, id=form_data['categoria'])

        if form_data['unidade']:
            unidade = get_object_or_404(Unidade, id=form_data['unidade'])

        if form_data['setor']:
            setor = get_object_or_404(Setor, id=form_data['setor'])

        if form_data['responsavel_revisao']:
            from django.contrib.auth import get_user_model
            Usuario = get_user_model()
            responsavel = get_object_or_404(Usuario, id=form_data['responsavel_revisao'])

        documento.titulo = form_data['titulo']
        documento.tipo = form_data['tipo']
        documento.categoria = categoria
        documento.unidade = unidade
        documento.setor = setor
        documento.descricao = form_data['descricao']
        documento.link_externo = form_data['link_externo']
        documento.versao = form_data['versao'] or '1.0'
        documento.status = form_data['status']
        documento.leitura_obrigatoria = form_data['leitura_obrigatoria']
        documento.responsavel_revisao = responsavel
        documento.data_revisao = form_data['data_revisao'] or None
        documento.ordem = int(form_data['ordem'] or 0)
        documento.ativo = form_data['ativo']
        documento.atualizado_por = request.user

        novo_arquivo = request.FILES.get('arquivo')

        if novo_arquivo:
            documento.arquivo = novo_arquivo

        documento.save()

        registrar_auditoria_base(
            request=request,
            acao='alterado',
            titulo=f'Documento alterado: {documento.titulo}',
            descricao=(
                f'Documento alterado na Base de Conhecimento.\n'
                f'Título: {documento.titulo}\n'
                f'Tipo: {documento.get_tipo_display()}\n'
                f'Status: {documento.get_status_display()}\n'
                f'Destino: {documento.destino_exibicao}'
            ),
            modelo='DocumentoConhecimento',
            objeto_id=documento.id,
        )

        messages.success(request, 'Documento atualizado com sucesso.')
        return redirect('/portal/modulos/base-conhecimento/')

    return render(request, 'base_conhecimento/formulario_documento.html', {
        'modo': 'editar',
        'form_data': form_data,
        'documento': documento,
        'categorias': categorias,
        'unidades': unidades,
        'setores': setores,
        'responsaveis': responsaveis,
        'tipos': DocumentoConhecimento.TIPO_CHOICES,
        'status_choices': DocumentoConhecimento.STATUS_CHOICES,
    })


@login_required(login_url='/')
def inativar_documento_conhecimento(request, documento_id):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    documento = get_object_or_404(
        aplicar_escopo_unidade(DocumentoConhecimento.objects.all(), request.user),
        id=documento_id,
    )
    documento.ativo = False
    documento.atualizado_por = request.user
    documento.save()

    registrar_auditoria_base(
        request=request,
        acao='alterado',
        titulo=f'Documento inativado: {documento.titulo}',
        descricao=f'Documento inativado na Base de Conhecimento: {documento.titulo}',
        modelo='DocumentoConhecimento',
        objeto_id=documento.id,
    )

    messages.success(request, 'Documento inativado com sucesso.')
    return redirect('/portal/modulos/base-conhecimento/')


@login_required(login_url='/')
def reativar_documento_conhecimento(request, documento_id):
    if not usuario_eh_admin_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    documento = get_object_or_404(
        aplicar_escopo_unidade(DocumentoConhecimento.objects.all(), request.user),
        id=documento_id,
    )
    documento.ativo = True
    documento.atualizado_por = request.user
    documento.save()

    registrar_auditoria_base(
        request=request,
        acao='alterado',
        titulo=f'Documento reativado: {documento.titulo}',
        descricao=f'Documento reativado na Base de Conhecimento: {documento.titulo}',
        modelo='DocumentoConhecimento',
        objeto_id=documento.id,
    )

    messages.success(request, 'Documento reativado com sucesso.')
    return redirect('/portal/modulos/base-conhecimento/')
