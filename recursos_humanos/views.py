from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from core.models import NotificacaoUsuario
from usuarios.escopo import aplicar_escopo_unidade, obter_unidade_ativa
from .forms import AtendimentoRHForm, SolicitacaoRHForm
from .models import AnexoRH, HistoricoRH, SolicitacaoRH


GRUPOS_RH = ('RH', 'TI Administrador')
EXTENSOES = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.jpg', '.jpeg', '.png'}
LIMITE = 10 * 1024 * 1024


def pode_atender(user):
    return user.is_superuser or user.groups.filter(name__in=GRUPOS_RH).exists()


def queryset_visivel(user):
    qs = aplicar_escopo_unidade(
        SolicitacaoRH.objects.select_related('unidade', 'setor', 'solicitante', 'responsavel'), user,
    )
    return qs if pode_atender(user) else qs.filter(solicitante=user)


def erros_anexos(arquivos):
    erros = []
    for arquivo in arquivos:
        nome = Path(arquivo.name).name
        if Path(nome).suffix.lower() not in EXTENSOES:
            erros.append(f'Arquivo não permitido: {nome}.')
        elif arquivo.size > LIMITE:
            erros.append(f'O arquivo {nome} excede 10 MB.')
    return erros


def salvar_anexos(solicitacao, arquivos, usuario):
    for arquivo in arquivos:
        AnexoRH.objects.create(
            solicitacao=solicitacao, arquivo=arquivo, nome_original=Path(arquivo.name).name,
            tipo_mime=arquivo.content_type or 'application/octet-stream',
            tamanho=arquivo.size, enviado_por=usuario,
        )


def registrar(solicitacao, usuario, anterior, novo, observacao=''):
    HistoricoRH.objects.create(
        solicitacao=solicitacao, usuario=usuario, status_anterior=anterior,
        status_novo=novo, observacao=observacao,
    )
    RegistroAuditoria.objects.create(
        modulo='sistema', acao='alterado' if anterior else 'criado',
        titulo=f'Solicitação RH #{solicitacao.pk}', descricao=f'{anterior or "Nova"} → {novo}',
        modelo='SolicitacaoRH', objeto_id=str(solicitacao.pk), usuario=usuario,
        unidade=solicitacao.unidade,
    )


def notificar_rh(solicitacao):
    usuarios = get_user_model().objects.filter(
        is_active=True, unidade=solicitacao.unidade, groups__name__in=GRUPOS_RH,
    ).distinct()
    for usuario in usuarios:
        NotificacaoUsuario.objects.update_or_create(
            usuario=usuario, origem='rh_nova', objeto_id=str(solicitacao.pk),
            defaults={
                'unidade': solicitacao.unidade, 'titulo': f'Nova solicitação de RH #{solicitacao.pk}',
                'descricao': solicitacao.assunto, 'tipo': 'warning', 'icone': '👥',
                'link': f'/portal/recursos-humanos/{solicitacao.pk}/', 'lida': False,
            },
        )


@login_required(login_url='/')
def lista(request):
    solicitacoes = queryset_visivel(request.user)
    busca = request.GET.get('busca', '').strip()
    status = request.GET.get('status', '').strip()
    if busca:
        solicitacoes = solicitacoes.filter(
            Q(assunto__icontains=busca) | Q(descricao__icontains=busca) |
            Q(solicitante__first_name__icontains=busca) | Q(solicitante__last_name__icontains=busca)
        )
    if status:
        solicitacoes = solicitacoes.filter(status=status)
    return render(request, 'recursos_humanos/lista.html', {
        'solicitacoes': solicitacoes, 'busca': busca, 'status_atual': status,
        'status_choices': SolicitacaoRH.STATUS_CHOICES,
        'pendentes': solicitacoes.filter(status='pendente').count(),
        'analise': solicitacoes.filter(status='em_analise').count(),
        'concluidas': solicitacoes.filter(status='concluida').count(),
    })


@login_required(login_url='/')
def nova(request):
    unidade = obter_unidade_ativa(request.user)
    if unidade is None:
        messages.error(request, 'Selecione uma unidade antes de continuar.')
        return redirect('rh_lista')
    form = SolicitacaoRHForm(request.POST or None, unidade=unidade)
    anexos = request.FILES.getlist('anexos') if request.method == 'POST' else []
    for erro in erros_anexos(anexos):
        form.add_error(None, erro)
    if request.method == 'POST' and form.is_valid():
        solicitacao = form.save(commit=False)
        solicitacao.unidade = unidade
        solicitacao.solicitante = request.user
        solicitacao.save()
        salvar_anexos(solicitacao, anexos, request.user)
        registrar(solicitacao, request.user, '', 'pendente')
        notificar_rh(solicitacao)
        messages.success(request, f'Solicitação #{solicitacao.pk} registrada.')
        return redirect('rh_detalhe', solicitacao_id=solicitacao.pk)
    return render(request, 'recursos_humanos/formulario.html', {'form': form})


@login_required(login_url='/')
def detalhe(request, solicitacao_id):
    solicitacao = get_object_or_404(queryset_visivel(request.user), pk=solicitacao_id)
    return render(request, 'recursos_humanos/detalhe.html', {
        'solicitacao': solicitacao, 'form': AtendimentoRHForm(instance=solicitacao),
        'pode_atender': pode_atender(request.user),
    })


@login_required(login_url='/')
def atender(request, solicitacao_id):
    if not pode_atender(request.user):
        messages.error(request, 'Você não possui permissão para este atendimento.')
        return redirect('rh_lista')
    solicitacao = get_object_or_404(
        aplicar_escopo_unidade(SolicitacaoRH.objects.all(), request.user), pk=solicitacao_id,
    )
    if request.method != 'POST':
        return redirect('rh_detalhe', solicitacao_id=solicitacao.pk)
    anterior = solicitacao.status
    form = AtendimentoRHForm(request.POST, instance=solicitacao)
    anexos = request.FILES.getlist('anexos')
    erros = erros_anexos(anexos)
    if form.is_valid() and not erros:
        solicitacao = form.save(commit=False)
        solicitacao.responsavel = request.user
        solicitacao.concluido_em = timezone.now() if solicitacao.status == 'concluida' else None
        solicitacao.save()
        salvar_anexos(solicitacao, anexos, request.user)
        registrar(solicitacao, request.user, anterior, solicitacao.status, solicitacao.resposta_rh)
        messages.success(request, 'Atendimento atualizado.')
    else:
        messages.error(request, ' '.join(erros) or 'Revise os dados.')
    return redirect('rh_detalhe', solicitacao_id=solicitacao.pk)


@login_required(login_url='/')
def baixar_anexo(request, anexo_id):
    anexo = get_object_or_404(AnexoRH.objects.select_related('solicitacao'), pk=anexo_id)
    if not queryset_visivel(request.user).filter(pk=anexo.solicitacao_id).exists():
        return render(request, 'core/sem_permissao.html', status=403)
    resposta = FileResponse(
        anexo.arquivo.open('rb'), as_attachment=True, filename=anexo.nome_original,
        content_type=anexo.tipo_mime,
    )
    resposta['X-Content-Type-Options'] = 'nosniff'
    return resposta
