from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    SolicitacaoInternaForm,
    AtendimentoSolicitacaoForm,
    ComentarioSolicitacaoForm,
)
from .models import SolicitacaoInterna
from .services import registrar_historico, rotulo_choice


@login_required
def solicitacoes_home(request):
    busca = request.GET.get('busca', '').strip()
    status = request.GET.get('status', '').strip()
    prioridade = request.GET.get('prioridade', '').strip()

    solicitacoes = SolicitacaoInterna.objects.select_related(
        'categoria',
        'solicitante',
        'responsavel',
        'unidade',
        'setor',
    )

    if busca:
        solicitacoes = solicitacoes.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(id__icontains=busca)
        )

    if status:
        solicitacoes = solicitacoes.filter(status=status)

    if prioridade:
        solicitacoes = solicitacoes.filter(prioridade=prioridade)

    totais = {
        'total': SolicitacaoInterna.objects.count(),
        'abertas': SolicitacaoInterna.objects.filter(status='aberta').count(),
        'andamento': SolicitacaoInterna.objects.filter(status='em_andamento').count(),
        'aguardando': SolicitacaoInterna.objects.filter(status='aguardando').count(),
        'concluidas': SolicitacaoInterna.objects.filter(status='concluida').count(),
        'criticas': SolicitacaoInterna.objects.filter(prioridade='critica').exclude(status='concluida').count(),
    }

    por_status = SolicitacaoInterna.objects.values('status').annotate(total=Count('id'))

    paginator = Paginator(solicitacoes, 10)
    pagina = request.GET.get('page')
    solicitacoes_pagina = paginator.get_page(pagina)

    context = {
        'solicitacoes': solicitacoes_pagina,
        'totais': totais,
        'por_status': por_status,
        'busca': busca,
        'status_atual': status,
        'prioridade_atual': prioridade,
        'status_choices': SolicitacaoInterna.STATUS_CHOICES,
        'prioridade_choices': SolicitacaoInterna.PRIORIDADE_CHOICES,
    }

    return render(request, 'solicitacoes/solicitacoes_home.html', context)


@login_required
def nova_solicitacao(request):
    if request.method == 'POST':
        form = SolicitacaoInternaForm(request.POST)

        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.solicitante = request.user
            solicitacao.unidade = getattr(request.user, 'unidade', None)
            solicitacao.setor = getattr(request.user, 'setor', None)
            solicitacao.save()

            registrar_historico(
                solicitacao=solicitacao,
                usuario=request.user,
                tipo='criacao',
                titulo='Solicitação criada',
                descricao='A solicitação foi aberta pelo usuário.',
                valor_novo=solicitacao.titulo,
            )

            return redirect('detalhe_solicitacao', solicitacao_id=solicitacao.id)
    else:
        form = SolicitacaoInternaForm()

    return render(request, 'solicitacoes/nova_solicitacao.html', {
        'form': form
    })


@login_required
def detalhe_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(
        SolicitacaoInterna.objects.select_related(
            'categoria',
            'solicitante',
            'responsavel',
            'unidade',
            'setor',
        ).prefetch_related(
            'comentarios',
            'historicos',
        ),
        id=solicitacao_id
    )

    comentario_form = ComentarioSolicitacaoForm()

    if request.method == 'POST':
        comentario_form = ComentarioSolicitacaoForm(request.POST)

        if comentario_form.is_valid():
            comentario = comentario_form.save(commit=False)
            comentario.solicitacao = solicitacao
            comentario.autor = request.user
            comentario.save()

            registrar_historico(
                solicitacao=solicitacao,
                usuario=request.user,
                tipo='comentario',
                titulo='Comentário adicionado',
                descricao=comentario.mensagem,
            )

            return redirect('detalhe_solicitacao', solicitacao_id=solicitacao.id)

    return render(request, 'solicitacoes/detalhe_solicitacao.html', {
        'solicitacao': solicitacao,
        'comentario_form': comentario_form,
    })


@login_required
def atender_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(
        SolicitacaoInterna.objects.select_related('responsavel'),
        id=solicitacao_id
    )

    status_anterior = solicitacao.status
    prioridade_anterior = solicitacao.prioridade
    responsavel_anterior = solicitacao.responsavel

    if request.method == 'POST':
        form = AtendimentoSolicitacaoForm(request.POST, instance=solicitacao)

        if form.is_valid():
            solicitacao_atualizada = form.save()

            if status_anterior != solicitacao_atualizada.status:
                registrar_historico(
                    solicitacao=solicitacao_atualizada,
                    usuario=request.user,
                    tipo='status',
                    titulo='Status alterado',
                    descricao='O status da solicitação foi atualizado.',
                    valor_anterior=rotulo_choice(SolicitacaoInterna.STATUS_CHOICES, status_anterior),
                    valor_novo=rotulo_choice(SolicitacaoInterna.STATUS_CHOICES, solicitacao_atualizada.status),
                )

                if solicitacao_atualizada.status == 'concluida':
                    registrar_historico(
                        solicitacao=solicitacao_atualizada,
                        usuario=request.user,
                        tipo='conclusao',
                        titulo='Solicitação concluída',
                        descricao='A solicitação foi marcada como concluída.',
                    )

            if prioridade_anterior != solicitacao_atualizada.prioridade:
                registrar_historico(
                    solicitacao=solicitacao_atualizada,
                    usuario=request.user,
                    tipo='prioridade',
                    titulo='Prioridade alterada',
                    descricao='A prioridade da solicitação foi atualizada.',
                    valor_anterior=rotulo_choice(SolicitacaoInterna.PRIORIDADE_CHOICES, prioridade_anterior),
                    valor_novo=rotulo_choice(SolicitacaoInterna.PRIORIDADE_CHOICES, solicitacao_atualizada.prioridade),
                )

            if responsavel_anterior != solicitacao_atualizada.responsavel:
                registrar_historico(
                    solicitacao=solicitacao_atualizada,
                    usuario=request.user,
                    tipo='responsavel',
                    titulo='Responsável alterado',
                    descricao='O responsável pela solicitação foi atualizado.',
                    valor_anterior=str(responsavel_anterior or 'Não atribuído'),
                    valor_novo=str(solicitacao_atualizada.responsavel or 'Não atribuído'),
                )

            return redirect('detalhe_solicitacao', solicitacao_id=solicitacao.id)
    else:
        form = AtendimentoSolicitacaoForm(instance=solicitacao)

    return render(request, 'solicitacoes/atender_solicitacao.html', {
        'form': form,
        'solicitacao': solicitacao,
    })