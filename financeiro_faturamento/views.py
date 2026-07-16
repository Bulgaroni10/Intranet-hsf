from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from usuarios.escopo import aplicar_escopo_unidade, obter_unidade_ativa
from .forms import RegistroFinanceiroForm
from .models import AnexoFinanceiro, HistoricoFinanceiro, RegistroFinanceiro

GRUPOS = ('Financeiro', 'Faturamento', 'Gerência', 'Diretoria', 'TI Administrador')
EXTENSOES = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.jpg', '.jpeg', '.png'}
LIMITE = 10 * 1024 * 1024


def permitido(user):
    return user.is_superuser or user.groups.filter(name__in=GRUPOS).exists()


def negar(request):
    return render(request, 'core/sem_permissao.html', status=403)


def queryset(user):
    return aplicar_escopo_unidade(
        RegistroFinanceiro.objects.select_related('unidade', 'criado_por', 'responsavel'), user,
    )


def validar(arquivos):
    erros = []
    for arquivo in arquivos:
        nome = Path(arquivo.name).name
        if Path(nome).suffix.lower() not in EXTENSOES:
            erros.append(f'Arquivo não permitido: {nome}.')
        elif arquivo.size > LIMITE:
            erros.append(f'{nome} excede 10 MB.')
    return erros


def anexar(registro, arquivos, usuario):
    for arquivo in arquivos:
        AnexoFinanceiro.objects.create(
            registro=registro, arquivo=arquivo, nome_original=Path(arquivo.name).name,
            tipo_mime=arquivo.content_type or 'application/octet-stream',
            tamanho=arquivo.size, enviado_por=usuario,
        )


@login_required(login_url='/')
def lista(request):
    if not permitido(request.user): return negar(request)
    registros = queryset(request.user)
    busca, area, status = (request.GET.get(x, '').strip() for x in ('busca', 'area', 'status'))
    if busca: registros = registros.filter(Q(titulo__icontains=busca) | Q(entidade__icontains=busca) | Q(descricao__icontains=busca))
    if area: registros = registros.filter(area=area)
    if status: registros = registros.filter(status=status)
    return render(request, 'financeiro_faturamento/lista.html', {
        'registros': registros, 'busca': busca, 'area_atual': area, 'status_atual': status,
        'areas': RegistroFinanceiro.AREA_CHOICES, 'status_choices': RegistroFinanceiro.STATUS_CHOICES,
        'pendentes': registros.exclude(status__in=['concluido', 'cancelado']).count(),
        'concluidos': registros.filter(status='concluido').count(),
        'valor_total': registros.aggregate(total=Sum('valor'))['total'] or 0,
    })


@login_required(login_url='/')
def editar(request, registro_id=None):
    if not permitido(request.user): return negar(request)
    unidade = obter_unidade_ativa(request.user)
    if unidade is None: return redirect('financeiro_lista')
    registro = get_object_or_404(queryset(request.user), pk=registro_id) if registro_id else None
    form = RegistroFinanceiroForm(request.POST or None, instance=registro, unidade=unidade)
    anexos = request.FILES.getlist('anexos') if request.method == 'POST' else []
    for erro in validar(anexos): form.add_error(None, erro)
    if request.method == 'POST' and form.is_valid():
        anterior = registro.status if registro else ''
        item = form.save(commit=False)
        if not registro: item.unidade, item.criado_por = unidade, request.user
        item.concluido_em = timezone.now() if item.status == 'concluido' else None
        item.save(); anexar(item, anexos, request.user)
        HistoricoFinanceiro.objects.create(registro=item, usuario=request.user, status_anterior=anterior, status_novo=item.status, observacao=item.observacao)
        RegistroAuditoria.objects.create(modulo='sistema', acao='alterado' if registro else 'criado', titulo=f'Financeiro/Faturamento #{item.pk}', descricao=item.titulo, modelo='RegistroFinanceiro', objeto_id=str(item.pk), usuario=request.user, unidade=item.unidade)
        messages.success(request, 'Registro salvo com sucesso.')
        return redirect('financeiro_detalhe', registro_id=item.pk)
    return render(request, 'financeiro_faturamento/formulario.html', {'form': form, 'registro': registro})


@login_required(login_url='/')
def detalhe(request, registro_id):
    if not permitido(request.user): return negar(request)
    return render(request, 'financeiro_faturamento/detalhe.html', {'registro': get_object_or_404(queryset(request.user), pk=registro_id)})


@login_required(login_url='/')
def baixar_anexo(request, anexo_id):
    if not permitido(request.user): return negar(request)
    anexo = get_object_or_404(AnexoFinanceiro.objects.select_related('registro'), pk=anexo_id)
    if not queryset(request.user).filter(pk=anexo.registro_id).exists(): return negar(request)
    resposta = FileResponse(anexo.arquivo.open('rb'), as_attachment=True, filename=anexo.nome_original, content_type=anexo.tipo_mime)
    resposta['X-Content-Type-Options'] = 'nosniff'; return resposta
