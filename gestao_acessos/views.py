from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from core.models import NotificacaoUsuario
from usuarios.escopo import aplicar_escopo_unidade, obter_unidade_ativa
from .forms import AtendimentoAcessoForm, SolicitacaoAcessoForm
from .models import HistoricoSolicitacaoAcesso, SolicitacaoAcesso


GRUPOS_TI = ('TI Administrador', 'TI Suporte')


def pode_gerenciar(user):
    return user.is_superuser or user.groups.filter(name__in=GRUPOS_TI).exists()


def queryset_visivel(user):
    qs = aplicar_escopo_unidade(
        SolicitacaoAcesso.objects.select_related(
            'unidade', 'setor', 'solicitante', 'responsavel',
        ), user,
    )
    if not pode_gerenciar(user):
        qs = qs.filter(solicitante=user)
    return qs


def registrar_evento(solicitacao, usuario, anterior, novo, observacao=''):
    HistoricoSolicitacaoAcesso.objects.create(
        solicitacao=solicitacao, usuario=usuario,
        status_anterior=anterior, status_novo=novo, observacao=observacao,
    )
    RegistroAuditoria.objects.create(
        modulo='sistema', acao='alterado' if anterior else 'criado',
        titulo=f'Gestão de Acessos #{solicitacao.pk}',
        descricao=f'{anterior or "Nova"} → {novo}. {observacao}'.strip(),
        modelo='SolicitacaoAcesso', objeto_id=str(solicitacao.pk),
        usuario=usuario, unidade=solicitacao.unidade,
    )


def notificar_ti(solicitacao):
    usuarios = get_user_model().objects.filter(
        is_active=True, unidade=solicitacao.unidade, groups__name__in=GRUPOS_TI,
    ).distinct()
    for usuario in usuarios:
        NotificacaoUsuario.objects.update_or_create(
            usuario=usuario, origem='gestao_acessos_nova',
            objeto_id=str(solicitacao.pk),
            defaults={
                'unidade': solicitacao.unidade,
                'titulo': f'Nova solicitação de acesso #{solicitacao.pk}',
                'descricao': solicitacao.colaborador_nome,
                'tipo': 'warning', 'icone': '🔐',
                'link': f'/portal/gestao-acessos/{solicitacao.pk}/',
                'lida': False,
            },
        )


@login_required(login_url='/')
def lista(request):
    solicitacoes = queryset_visivel(request.user)
    busca = request.GET.get('busca', '').strip()
    status = request.GET.get('status', '').strip()
    if busca:
        solicitacoes = solicitacoes.filter(
            Q(colaborador_nome__icontains=busca) |
            Q(colaborador_matricula__icontains=busca) |
            Q(sistemas__icontains=busca)
        )
    if status:
        solicitacoes = solicitacoes.filter(status=status)
    contexto = {
        'solicitacoes': solicitacoes,
        'pode_gerenciar': pode_gerenciar(request.user),
        'status_choices': SolicitacaoAcesso.STATUS_CHOICES,
        'busca': busca, 'status_atual': status,
        'total_pendentes': solicitacoes.filter(status='pendente').count(),
        'total_execucao': solicitacoes.filter(status='em_execucao').count(),
        'total_concluidas': solicitacoes.filter(status='concluida').count(),
    }
    return render(request, 'gestao_acessos/lista.html', contexto)


@login_required(login_url='/')
def nova(request):
    unidade = obter_unidade_ativa(request.user)
    if unidade is None:
        messages.error(request, 'Selecione uma unidade antes de continuar.')
        return redirect('gestao_acessos_lista')
    form = SolicitacaoAcessoForm(request.POST or None, unidade=unidade)
    if request.method == 'POST' and form.is_valid():
        solicitacao = form.save(commit=False)
        solicitacao.unidade = unidade
        solicitacao.solicitante = request.user
        solicitacao.save()
        registrar_evento(solicitacao, request.user, '', 'pendente', 'Solicitação aberta.')
        notificar_ti(solicitacao)
        messages.success(request, f'Solicitação #{solicitacao.pk} criada com sucesso.')
        return redirect('gestao_acessos_detalhe', solicitacao_id=solicitacao.pk)
    return render(request, 'gestao_acessos/formulario.html', {'form': form})


@login_required(login_url='/')
def detalhe(request, solicitacao_id):
    solicitacao = get_object_or_404(queryset_visivel(request.user), pk=solicitacao_id)
    form = AtendimentoAcessoForm(instance=solicitacao)
    return render(request, 'gestao_acessos/detalhe.html', {
        'solicitacao': solicitacao, 'form': form,
        'pode_gerenciar': pode_gerenciar(request.user),
    })


@login_required(login_url='/')
def atender(request, solicitacao_id):
    if not pode_gerenciar(request.user):
        messages.error(request, 'Você não possui permissão para atender solicitações.')
        return redirect('gestao_acessos_lista')
    solicitacao = get_object_or_404(
        aplicar_escopo_unidade(SolicitacaoAcesso.objects.all(), request.user),
        pk=solicitacao_id,
    )
    if request.method != 'POST':
        return redirect('gestao_acessos_detalhe', solicitacao_id=solicitacao.pk)
    anterior = solicitacao.status
    form = AtendimentoAcessoForm(request.POST, instance=solicitacao)
    if form.is_valid():
        solicitacao = form.save(commit=False)
        solicitacao.responsavel = request.user
        solicitacao.concluido_em = timezone.now() if solicitacao.status == 'concluida' else None
        solicitacao.save()
        registrar_evento(
            solicitacao, request.user, anterior, solicitacao.status,
            solicitacao.observacao_ti,
        )
        messages.success(request, 'Atendimento atualizado com sucesso.')
    else:
        messages.error(request, 'Revise os dados informados.')
    return redirect('gestao_acessos_detalhe', solicitacao_id=solicitacao.pk)
