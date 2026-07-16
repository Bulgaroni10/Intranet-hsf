from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.models import RegistroAuditoria
from usuarios.escopo import aplicar_escopo_unidade, obter_unidade_ativa
from .forms import ExameForm
from .models import DocumentoExame, ExameLaboratorial

GRUPOS_CONSULTA = ('Laboratório', 'Recepção', 'Médico', 'Enfermagem', 'Gerência', 'Diretoria', 'TI Administrador')
GRUPOS_EDICAO = ('Laboratório', 'TI Administrador')
EXTENSOES = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.jpg', '.jpeg', '.png'}
LIMITE = 10 * 1024 * 1024


def tem_grupo(user, grupos):
    return user.is_superuser or user.groups.filter(name__in=grupos).exists()


def negar(request): return render(request, 'core/sem_permissao.html', status=403)


def queryset(user):
    return aplicar_escopo_unidade(ExameLaboratorial.objects.select_related('unidade', 'criado_por'), user)


def validar(arquivos):
    erros = []
    for arquivo in arquivos:
        nome = Path(arquivo.name).name
        if Path(nome).suffix.lower() not in EXTENSOES: erros.append(f'Arquivo não permitido: {nome}.')
        elif arquivo.size > LIMITE: erros.append(f'{nome} excede 10 MB.')
    return erros


def anexar(exame, arquivos, usuario):
    for arquivo in arquivos:
        DocumentoExame.objects.create(
            exame=exame, arquivo=arquivo, nome_original=Path(arquivo.name).name,
            tipo_mime=arquivo.content_type or 'application/octet-stream', tamanho=arquivo.size,
            enviado_por=usuario,
        )


@login_required(login_url='/')
def lista(request):
    if not tem_grupo(request.user, GRUPOS_CONSULTA): return negar(request)
    exames = queryset(request.user)
    busca, categoria = request.GET.get('busca', '').strip(), request.GET.get('categoria', '').strip()
    if busca:
        exames = exames.filter(Q(nome__icontains=busca) | Q(codigo__icontains=busca) | Q(sinonimos__icontains=busca) | Q(material__icontains=busca))
    if categoria: exames = exames.filter(categoria=categoria)
    return render(request, 'laboratorio/lista.html', {
        'exames': exames, 'busca': busca, 'categoria_atual': categoria,
        'categorias': ExameLaboratorial.CATEGORIA_CHOICES,
        'total': exames.count(), 'ativos': exames.filter(ativo=True).count(),
        'pode_editar': tem_grupo(request.user, GRUPOS_EDICAO),
    })


@login_required(login_url='/')
def editar(request, exame_id=None):
    if not tem_grupo(request.user, GRUPOS_EDICAO): return negar(request)
    unidade = obter_unidade_ativa(request.user)
    if unidade is None: return redirect('laboratorio_lista')
    exame = get_object_or_404(queryset(request.user), pk=exame_id) if exame_id else None
    form = ExameForm(request.POST or None, instance=exame)
    arquivos = request.FILES.getlist('documentos') if request.method == 'POST' else []
    for erro in validar(arquivos): form.add_error(None, erro)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        if not exame: item.unidade, item.criado_por = unidade, request.user
        item.save(); anexar(item, arquivos, request.user)
        RegistroAuditoria.objects.create(
            modulo='sistema', acao='alterado' if exame else 'criado', titulo=f'Exame: {item.nome}',
            descricao=f'Cadastro laboratorial da unidade {item.unidade.sigla}.', modelo='ExameLaboratorial',
            objeto_id=str(item.pk), usuario=request.user, unidade=item.unidade,
        )
        messages.success(request, 'Exame salvo com sucesso.')
        return redirect('laboratorio_detalhe', exame_id=item.pk)
    return render(request, 'laboratorio/formulario.html', {'form': form, 'exame': exame})


@login_required(login_url='/')
def detalhe(request, exame_id):
    if not tem_grupo(request.user, GRUPOS_CONSULTA): return negar(request)
    return render(request, 'laboratorio/detalhe.html', {
        'exame': get_object_or_404(queryset(request.user), pk=exame_id),
        'pode_editar': tem_grupo(request.user, GRUPOS_EDICAO),
    })


@login_required(login_url='/')
def baixar_documento(request, documento_id):
    if not tem_grupo(request.user, GRUPOS_CONSULTA): return negar(request)
    documento = get_object_or_404(DocumentoExame.objects.select_related('exame'), pk=documento_id)
    if not queryset(request.user).filter(pk=documento.exame_id).exists(): return negar(request)
    resposta = FileResponse(documento.arquivo.open('rb'), as_attachment=True, filename=documento.nome_original, content_type=documento.tipo_mime)
    resposta['X-Content-Type-Options'] = 'nosniff'; return resposta
