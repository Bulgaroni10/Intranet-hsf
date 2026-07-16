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
from .forms import AtendimentoAcessoRemotoForm, SolicitacaoAcessoRemotoForm
from .models import AnexoAcessoRemoto, HistoricoAcessoRemoto, SolicitacaoAcessoRemoto


GRUPOS_TI = ('TI Administrador', 'TI Suporte')
EXTENSOES = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.jpg', '.jpeg', '.png'}
LIMITE = 10 * 1024 * 1024


def pode_gerenciar(user):
    return user.is_superuser or user.groups.filter(name__in=GRUPOS_TI).exists()


def queryset_visivel(user):
    qs = aplicar_escopo_unidade(
        SolicitacaoAcessoRemoto.objects.select_related(
            'unidade', 'setor', 'solicitante', 'responsavel',
        ), user,
    )
    return qs if pode_gerenciar(user) else qs.filter(solicitante=user)


def validar_anexos(arquivos):
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
        AnexoAcessoRemoto.objects.create(
            solicitacao=solicitacao, arquivo=arquivo,
            nome_original=Path(arquivo.name).name,
            tipo_mime=arquivo.content_type or 'application/octet-stream',
            tamanho=arquivo.size, enviado_por=usuario,
        )


def registrar_evento(solicitacao, usuario, anterior, novo, observacao=''):
    HistoricoAcessoRemoto.objects.create(
        solicitacao=solicitacao, usuario=usuario, status_anterior=anterior,
        status_novo=novo, observacao=observacao,
    )
    RegistroAuditoria.objects.create(
        modulo='sistema', acao='alterado' if anterior else 'criado',
        titulo=f'Acesso Remoto #{solicitacao.pk}',
        descricao=f'{anterior or "Nova"} → {novo}. {observacao}'.strip(),
        modelo='SolicitacaoAcessoRemoto', objeto_id=str(solicitacao.pk),
        usuario=usuario, unidade=solicitacao.unidade,
    )


def notificar_ti(solicitacao):
    usuarios = get_user_model().objects.filter(
        is_active=True, unidade=solicitacao.unidade, groups__name__in=GRUPOS_TI,
    ).distinct()
    for usuario in usuarios:
        NotificacaoUsuario.objects.update_or_create(
            usuario=usuario, origem='acesso_remoto_novo', objeto_id=str(solicitacao.pk),
            defaults={
                'unidade': solicitacao.unidade,
                'titulo': f'Nova solicitação de VPN #{solicitacao.pk}',
                'descricao': solicitacao.nome, 'tipo': 'warning', 'icone': '🌐',
                'link': f'/portal/acesso-remoto/{solicitacao.pk}/', 'lida': False,
            },
        )


@login_required(login_url='/')
def lista(request):
    solicitacoes = queryset_visivel(request.user)
    busca = request.GET.get('busca', '').strip()
    status = request.GET.get('status', '').strip()
    if busca:
        solicitacoes = solicitacoes.filter(
            Q(nome__icontains=busca) | Q(cpf__icontains=busca) |
            Q(sistema_destino__icontains=busca) | Q(empresa_terceira__icontains=busca)
        )
    if status:
        solicitacoes = solicitacoes.filter(status=status)
    return render(request, 'acesso_remoto/lista.html', {
        'solicitacoes': solicitacoes, 'busca': busca, 'status_atual': status,
        'status_choices': SolicitacaoAcessoRemoto.STATUS_CHOICES,
        'total_pendentes': solicitacoes.filter(status='pendente').count(),
        'total_ativas': solicitacoes.filter(status='ativa').count(),
        'total_encerradas': solicitacoes.filter(status='encerrada').count(),
    })


@login_required(login_url='/')
def nova(request):
    unidade = obter_unidade_ativa(request.user)
    if unidade is None:
        messages.error(request, 'Selecione uma unidade antes de continuar.')
        return redirect('acesso_remoto_lista')
    form = SolicitacaoAcessoRemotoForm(request.POST or None, unidade=unidade)
    anexos = request.FILES.getlist('anexos') if request.method == 'POST' else []
    for erro in validar_anexos(anexos):
        form.add_error(None, erro)
    if request.method == 'POST' and form.is_valid():
        solicitacao = form.save(commit=False)
        solicitacao.unidade = unidade
        solicitacao.solicitante = request.user
        solicitacao.save()
        salvar_anexos(solicitacao, anexos, request.user)
        registrar_evento(solicitacao, request.user, '', 'pendente', 'Solicitação aberta.')
        notificar_ti(solicitacao)
        messages.success(request, f'Solicitação #{solicitacao.pk} criada com sucesso.')
        return redirect('acesso_remoto_detalhe', solicitacao_id=solicitacao.pk)
    return render(request, 'acesso_remoto/formulario.html', {'form': form})


@login_required(login_url='/')
def detalhe(request, solicitacao_id):
    solicitacao = get_object_or_404(queryset_visivel(request.user), pk=solicitacao_id)
    return render(request, 'acesso_remoto/detalhe.html', {
        'solicitacao': solicitacao,
        'form': AtendimentoAcessoRemotoForm(instance=solicitacao),
        'pode_gerenciar': pode_gerenciar(request.user),
    })


@login_required(login_url='/')
def atender(request, solicitacao_id):
    if not pode_gerenciar(request.user):
        messages.error(request, 'Você não possui permissão para atender esta solicitação.')
        return redirect('acesso_remoto_lista')
    solicitacao = get_object_or_404(
        aplicar_escopo_unidade(SolicitacaoAcessoRemoto.objects.all(), request.user),
        pk=solicitacao_id,
    )
    if request.method != 'POST':
        return redirect('acesso_remoto_detalhe', solicitacao_id=solicitacao.pk)
    anterior = solicitacao.status
    form = AtendimentoAcessoRemotoForm(request.POST, instance=solicitacao)
    anexos = request.FILES.getlist('anexos')
    erros = validar_anexos(anexos)
    if form.is_valid() and not erros:
        solicitacao = form.save(commit=False)
        solicitacao.responsavel = request.user
        solicitacao.encerrado_em = timezone.now() if solicitacao.status in {'encerrada', 'cancelada'} else None
        solicitacao.save()
        salvar_anexos(solicitacao, anexos, request.user)
        registrar_evento(solicitacao, request.user, anterior, solicitacao.status, solicitacao.observacao_ti)
        messages.success(request, 'Atendimento atualizado com sucesso.')
    else:
        messages.error(request, ' '.join(erros) or 'Revise os dados informados.')
    return redirect('acesso_remoto_detalhe', solicitacao_id=solicitacao.pk)


@login_required(login_url='/')
def baixar_anexo(request, anexo_id):
    anexo = get_object_or_404(AnexoAcessoRemoto.objects.select_related('solicitacao'), pk=anexo_id)
    if not queryset_visivel(request.user).filter(pk=anexo.solicitacao_id).exists():
        return render(request, 'core/sem_permissao.html', status=403)
    resposta = FileResponse(
        anexo.arquivo.open('rb'), as_attachment=True, filename=anexo.nome_original,
        content_type=anexo.tipo_mime,
    )
    resposta['X-Content-Type-Options'] = 'nosniff'
    return resposta
