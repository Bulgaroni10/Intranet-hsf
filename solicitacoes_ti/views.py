import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from auditoria.models import RegistroAuditoria
from modulos.models import Modulo
from usuarios.models import Unidade, Setor, Usuario
from .models import SolicitacaoTI, MensagemSolicitacaoTI


NOME_MODULO_SOLICITACOES_TI = 'Solicitações Internas de TI'


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


def usuario_pode_gerenciar_solicitacoes(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def obter_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def modulo_origem_valido(valor):
    valores_validos = [
        item[0]
        for item in SolicitacaoTI.MODULO_ORIGEM_CHOICES
    ]

    if valor in valores_validos:
        return valor

    return 'portal'


def registrar_auditoria_solicitacao(request, solicitacao, acao, titulo, descricao_extra=''):
    RegistroAuditoria.objects.create(
        modulo='sistema',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Solicitação: #{solicitacao.id} - {solicitacao.titulo}\n'
            f'Módulo de origem: {solicitacao.modulo_origem_exibicao}\n'
            f'Tipo: {solicitacao.get_tipo_display()}\n'
            f'Prioridade: {solicitacao.get_prioridade_display()}\n'
            f'Status: {solicitacao.get_status_display()}\n'
            f'SLA: {solicitacao.sla_status_exibicao}\n'
            f'Prazo SLA: {timezone.localtime(solicitacao.sla_prazo_em).strftime("%d/%m/%Y %H:%M") if solicitacao.sla_prazo_em else "Não definido"}\n'
            f'Unidade: {solicitacao.unidade.nome if solicitacao.unidade else "Não informada"}\n'
            f'Setor: {solicitacao.setor.nome if solicitacao.setor else "Não informado"}\n'
            f'Solicitante: {solicitacao.solicitante.get_full_name() if solicitacao.solicitante and solicitacao.solicitante.get_full_name() else solicitacao.solicitante.username if solicitacao.solicitante else "Não informado"}\n'
            f'Responsável TI: {solicitacao.responsavel_ti.get_full_name() if solicitacao.responsavel_ti and solicitacao.responsavel_ti.get_full_name() else solicitacao.responsavel_ti.username if solicitacao.responsavel_ti else "Não definido"}\n'
            f'Equipamento / referência: {solicitacao.equipamento or "Não informado"}\n'
            f'Visto pela TI: {"Sim" if solicitacao.visto_pela_ti else "Não"}\n'
            f'Conversa iniciada: {"Sim" if solicitacao.conversa_iniciada else "Não"}\n'
            f'Resolvido em: {timezone.localtime(solicitacao.resolvido_em).strftime("%d/%m/%Y %H:%M") if solicitacao.resolvido_em else "Não resolvido"}'
            f'{descricao_extra}'
        ),
        modelo='SolicitacaoTI',
        objeto_id=str(solicitacao.id),
        usuario=request.user,
        unidade=solicitacao.unidade,
        ip_origem=obter_ip_cliente(request),
    )


def atualizar_sla_queryset(solicitacoes):
    for solicitacao in solicitacoes:
        solicitacao.atualizar_sla(salvar=True)


def buscar_solicitacoes_filtradas(request):
    pode_gerenciar = usuario_pode_gerenciar_solicitacoes(request.user)

    if pode_gerenciar:
        solicitacoes = SolicitacaoTI.objects.filter(
            ativo=True,
            unidade=getattr(request.user, 'unidade', None),
        ).select_related(
            'unidade',
            'setor',
            'solicitante',
            'responsavel_ti',
        ).prefetch_related(
            'mensagens'
        )
    else:
        solicitacoes = SolicitacaoTI.objects.filter(
            ativo=True,
            solicitante=request.user,
        ).select_related(
            'unidade',
            'setor',
            'solicitante',
            'responsavel_ti',
        ).prefetch_related(
            'mensagens'
        )

    busca = request.GET.get('busca', '').strip()
    modulo_origem = request.GET.get('modulo_origem', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    prioridade = request.GET.get('prioridade', '').strip()
    status = request.GET.get('status', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    responsavel_id = request.GET.get('responsavel', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()
    sla = request.GET.get('sla', '').strip()

    if busca:
        solicitacoes = solicitacoes.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(equipamento__icontains=busca) |
            Q(resposta_ti__icontains=busca) |
            Q(solicitante__username__icontains=busca) |
            Q(solicitante__first_name__icontains=busca) |
            Q(solicitante__last_name__icontains=busca) |
            Q(responsavel_ti__username__icontains=busca) |
            Q(responsavel_ti__first_name__icontains=busca) |
            Q(responsavel_ti__last_name__icontains=busca)
        )

    if modulo_origem:
        solicitacoes = solicitacoes.filter(
            modulo_origem=modulo_origem_valido(modulo_origem)
        )

    if tipo:
        solicitacoes = solicitacoes.filter(tipo=tipo)

    if prioridade:
        solicitacoes = solicitacoes.filter(prioridade=prioridade)

    if status:
        solicitacoes = solicitacoes.filter(status=status)

    if unidade_id:
        solicitacoes = solicitacoes.filter(unidade_id=unidade_id)

    if responsavel_id:
        if responsavel_id == 'sem_responsavel':
            solicitacoes = solicitacoes.filter(responsavel_ti__isnull=True)
        else:
            solicitacoes = solicitacoes.filter(responsavel_ti_id=responsavel_id)

    if data_inicio:
        solicitacoes = solicitacoes.filter(criado_em__date__gte=data_inicio)

    if data_fim:
        solicitacoes = solicitacoes.filter(criado_em__date__lte=data_fim)

    if sla:
        solicitacoes = solicitacoes.filter(sla_status=sla)

    return solicitacoes.order_by('-criado_em')


@login_required(login_url='/')
def solicitacoes_ti(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_SOLICITACOES_TI):
        return render(request, 'core/sem_permissao.html', status=403)

    pode_gerenciar = usuario_pode_gerenciar_solicitacoes(request.user)

    solicitacoes = buscar_solicitacoes_filtradas(request)

    atualizar_sla_queryset(solicitacoes[:300])

    solicitacoes = buscar_solicitacoes_filtradas(request)

    busca = request.GET.get('busca', '').strip()
    modulo_origem = request.GET.get('modulo_origem', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    prioridade = request.GET.get('prioridade', '').strip()
    status = request.GET.get('status', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    responsavel_id = request.GET.get('responsavel', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()
    sla = request.GET.get('sla', '').strip()

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    responsaveis_ti = Usuario.objects.filter(
        Q(is_superuser=True) |
        Q(groups__name='TI Administrador') |
        Q(solicitacoes_ti_responsavel__isnull=False)
    ).distinct().order_by(
        'first_name',
        'last_name',
        'username'
    )

    total_solicitacoes = solicitacoes.count()
    total_abertas = solicitacoes.filter(status='aberto').count()
    total_atendimento = solicitacoes.filter(status='em_atendimento').count()
    total_aguardando = solicitacoes.filter(
        Q(status='aguardando_usuario') |
        Q(status='aguardando_terceiro')
    ).count()
    total_resolvidas = solicitacoes.filter(status='resolvido').count()
    total_sla_estourado = solicitacoes.filter(sla_status='estourado').count()
    total_sla_alerta = solicitacoes.filter(sla_status='proximo_vencimento').count()

    notificacoes_usuario = MensagemSolicitacaoTI.objects.none()

    if not pode_gerenciar:
        notificacoes_usuario = MensagemSolicitacaoTI.objects.filter(
            solicitacao__ativo=True,
            solicitacao__solicitante=request.user,
            lida_pelo_solicitante=False
        ).exclude(
            origem='solicitante'
        ).select_related(
            'solicitacao',
            'autor'
        ).order_by(
            '-criado_em'
        )[:10]

    return render(request, 'solicitacoes_ti/solicitacoes_ti.html', {
        'page_title': 'Solicitações de TI',
        'solicitacoes': solicitacoes[:300],
        'unidades': unidades,
        'responsaveis_ti': responsaveis_ti,
        'modulos_origem': SolicitacaoTI.MODULO_ORIGEM_CHOICES,
        'tipos': SolicitacaoTI.TIPO_CHOICES,
        'prioridades': SolicitacaoTI.PRIORIDADE_CHOICES,
        'status_choices': SolicitacaoTI.STATUS_CHOICES,
        'sla_choices': SolicitacaoTI.SLA_STATUS_CHOICES,
        'busca': busca,
        'modulo_origem': modulo_origem,
        'tipo': tipo,
        'prioridade': prioridade,
        'status': status,
        'unidade_id': unidade_id,
        'responsavel_id': responsavel_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'sla': sla,
        'total_solicitacoes': total_solicitacoes,
        'total_abertas': total_abertas,
        'total_atendimento': total_atendimento,
        'total_aguardando': total_aguardando,
        'total_resolvidas': total_resolvidas,
        'total_sla_estourado': total_sla_estourado,
        'total_sla_alerta': total_sla_alerta,
        'pode_gerenciar': pode_gerenciar,
        'notificacoes_usuario': notificacoes_usuario,
        'total_notificacoes_usuario': len(notificacoes_usuario),
        'query_string': request.GET.urlencode(),
    })


@login_required(login_url='/')
def exportar_solicitacoes_ti_csv(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_SOLICITACOES_TI):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_solicitacoes(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    solicitacoes = buscar_solicitacoes_filtradas(request)

    atualizar_sla_queryset(solicitacoes[:1000])

    solicitacoes = buscar_solicitacoes_filtradas(request)

    nome_arquivo = f'solicitacoes_ti_{timezone.localdate().strftime("%Y%m%d")}.csv'

    response = HttpResponse(
        content_type='text/csv; charset=utf-8-sig'
    )
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'

    response.write('\ufeff')

    writer = csv.writer(
        response,
        delimiter=';',
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )

    writer.writerow([
        'ID',
        'Título',
        'Módulo de origem',
        'Tipo',
        'Prioridade',
        'Status',
        'SLA',
        'Prazo SLA',
        'Tempo restante / atraso',
        'Unidade',
        'Setor',
        'Solicitante',
        'Responsável TI',
        'Equipamento / Referência',
        'Descrição',
        'Resposta TI',
        'Visto pela TI',
        'Conversa iniciada',
        'Criado em',
        'Atualizado em',
        'Resolvido em',
    ])

    for solicitacao in solicitacoes:
        writer.writerow([
            solicitacao.id,
            solicitacao.titulo,
            solicitacao.modulo_origem_exibicao,
            solicitacao.get_tipo_display(),
            solicitacao.get_prioridade_display(),
            solicitacao.get_status_display(),
            solicitacao.sla_status_exibicao,
            timezone.localtime(solicitacao.sla_prazo_em).strftime('%d/%m/%Y %H:%M') if solicitacao.sla_prazo_em else '',
            solicitacao.tempo_restante_sla,
            solicitacao.unidade.nome if solicitacao.unidade else '',
            solicitacao.setor.nome if solicitacao.setor else '',
            solicitacao.solicitante.get_full_name() or solicitacao.solicitante.username if solicitacao.solicitante else '',
            solicitacao.responsavel_ti.get_full_name() or solicitacao.responsavel_ti.username if solicitacao.responsavel_ti else '',
            solicitacao.equipamento,
            solicitacao.descricao,
            solicitacao.resposta_ti,
            'Sim' if solicitacao.visto_pela_ti else 'Não',
            'Sim' if solicitacao.conversa_iniciada else 'Não',
            timezone.localtime(solicitacao.criado_em).strftime('%d/%m/%Y %H:%M') if solicitacao.criado_em else '',
            timezone.localtime(solicitacao.atualizado_em).strftime('%d/%m/%Y %H:%M') if solicitacao.atualizado_em else '',
            timezone.localtime(solicitacao.resolvido_em).strftime('%d/%m/%Y %H:%M') if solicitacao.resolvido_em else '',
        ])

    return response


@login_required(login_url='/')
def nova_solicitacao_ti(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_SOLICITACOES_TI):
        return render(request, 'core/sem_permissao.html', status=403)

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

    erro = ''

    modulo_origem_inicial = modulo_origem_valido(
        request.GET.get('modulo', '').strip() or
        request.GET.get('modulo_origem', '').strip() or
        'portal'
    )

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        modulo_origem = modulo_origem_valido(request.POST.get('modulo_origem', '').strip())
        tipo = request.POST.get('tipo', '').strip()
        prioridade = request.POST.get('prioridade', '').strip()
        unidade_id = request.POST.get('unidade', '').strip()
        setor_id = request.POST.get('setor', '').strip()
        equipamento = request.POST.get('equipamento', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        anexo = request.FILES.get('anexo')

        if not titulo or not tipo or not prioridade or not descricao:
            erro = 'Preencha título, tipo, prioridade e descrição.'
        else:
            unidade = request.user.unidade

            if unidade_id and usuario_pode_gerenciar_solicitacoes(request.user):
                unidade = Unidade.objects.filter(id=unidade_id, ativo=True).first()

            setor = request.user.setor

            if setor_id:
                setor = Setor.objects.filter(id=setor_id, ativo=True).first()

            solicitacao = SolicitacaoTI.objects.create(
                titulo=titulo,
                modulo_origem=modulo_origem,
                tipo=tipo,
                prioridade=prioridade,
                unidade=unidade,
                setor=setor,
                solicitante=request.user,
                equipamento=equipamento,
                descricao=descricao,
                anexo=anexo,
                status='aberto',
                ativo=True,
            )

            solicitacao.atualizar_sla(salvar=True)

            MensagemSolicitacaoTI.objects.create(
                solicitacao=solicitacao,
                autor=request.user,
                origem='sistema',
                mensagem=f'Solicitação aberta pelo usuário no módulo: {solicitacao.modulo_origem_exibicao}.',
                lida_pela_ti=False,
                lida_pelo_solicitante=True,
            )

            registrar_auditoria_solicitacao(
                request=request,
                solicitacao=solicitacao,
                acao='criado',
                titulo=f'Solicitação de TI criada: #{solicitacao.id} - {solicitacao.titulo}',
                descricao_extra=(
                    f'\n\nDescrição inicial:\n{solicitacao.descricao}'
                )
            )

            return redirect('solicitacoes_ti')

    return render(request, 'solicitacoes_ti/nova_solicitacao_ti.html', {
        'page_title': 'Nova solicitação de TI',
        'unidades': unidades,
        'setores': setores,
        'modulos_origem': SolicitacaoTI.MODULO_ORIGEM_CHOICES,
        'modulo_origem_inicial': modulo_origem_inicial,
        'tipos': SolicitacaoTI.TIPO_CHOICES,
        'prioridades': SolicitacaoTI.PRIORIDADE_CHOICES,
        'erro': erro,
        'pode_gerenciar': usuario_pode_gerenciar_solicitacoes(request.user),
    })


@login_required(login_url='/')
def detalhe_solicitacao_ti(request, solicitacao_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_SOLICITACOES_TI):
        return render(request, 'core/sem_permissao.html', status=403)

    pode_gerenciar = usuario_pode_gerenciar_solicitacoes(request.user)

    if pode_gerenciar:
        solicitacao = get_object_or_404(
            SolicitacaoTI.objects.select_related(
                'unidade',
                'setor',
                'solicitante',
                'responsavel_ti',
            ),
            id=solicitacao_id,
            ativo=True,
            unidade=getattr(request.user, 'unidade', None),
        )
    else:
        solicitacao = get_object_or_404(
            SolicitacaoTI.objects.select_related(
                'unidade',
                'setor',
                'solicitante',
                'responsavel_ti',
            ),
            id=solicitacao_id,
            ativo=True,
            solicitante=request.user
        )

    solicitacao.atualizar_sla(salvar=True)

    erro = ''
    sucesso = ''

    if request.method == 'POST':
        mensagem = request.POST.get('mensagem', '').strip()

        if not solicitacao.conversa_iniciada:
            erro = 'A conversa ainda não foi iniciada pela TI.'
        elif solicitacao.esta_encerrada:
            erro = 'Esta solicitação já está encerrada.'
        elif not mensagem:
            erro = 'Digite uma mensagem antes de enviar.'
        else:
            origem = 'ti' if pode_gerenciar else 'solicitante'

            MensagemSolicitacaoTI.objects.create(
                solicitacao=solicitacao,
                autor=request.user,
                origem=origem,
                mensagem=mensagem,
                lida_pela_ti=True if origem == 'ti' else False,
                lida_pelo_solicitante=True if origem == 'solicitante' else False,
            )

            if origem == 'solicitante':
                solicitacao.status = 'em_atendimento'
                solicitacao.save()
                solicitacao.atualizar_sla(salvar=True)

            registrar_auditoria_solicitacao(
                request=request,
                solicitacao=solicitacao,
                acao='alterado',
                titulo=f'Mensagem registrada na solicitação: #{solicitacao.id}',
                descricao_extra=(
                    f'\n\nOrigem da mensagem: {origem}\n'
                    f'Mensagem:\n{mensagem}'
                )
            )

            sucesso = 'Mensagem registrada.'

    if pode_gerenciar:
        MensagemSolicitacaoTI.objects.filter(
            solicitacao=solicitacao,
            origem='solicitante'
        ).update(
            lida_pela_ti=True
        )
    else:
        MensagemSolicitacaoTI.objects.filter(
            solicitacao=solicitacao
        ).exclude(
            origem='solicitante'
        ).update(
            lida_pelo_solicitante=True
        )

    mensagens = solicitacao.mensagens.select_related(
        'autor'
    ).order_by(
        'criado_em'
    )

    return render(request, 'solicitacoes_ti/detalhe_solicitacao_ti.html', {
        'page_title': f'Solicitação #{solicitacao.id}',
        'solicitacao': solicitacao,
        'mensagens': mensagens,
        'erro': erro,
        'sucesso': sucesso,
        'pode_gerenciar': pode_gerenciar,
    })


@login_required(login_url='/')
def atender_solicitacao_ti(request, solicitacao_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_SOLICITACOES_TI):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_solicitacoes(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    solicitacao = get_object_or_404(
        SolicitacaoTI.objects.select_related(
            'unidade',
            'setor',
            'solicitante',
            'responsavel_ti',
        ),
        id=solicitacao_id,
        ativo=True,
        unidade=getattr(request.user, 'unidade', None),
    )

    solicitacao.atualizar_sla(salvar=True)

    erro = ''
    sucesso = ''

    if request.method == 'POST':
        acao = request.POST.get('acao', '').strip()

        if acao == 'assumir':
            solicitacao.marcar_como_vista(request.user)
            solicitacao.atualizar_sla(salvar=True)

            MensagemSolicitacaoTI.objects.create(
                solicitacao=solicitacao,
                autor=request.user,
                origem='sistema',
                mensagem='Sua solicitação foi visualizada e está em análise pela TI.',
                lida_pela_ti=True,
                lida_pelo_solicitante=False,
            )

            registrar_auditoria_solicitacao(
                request=request,
                solicitacao=solicitacao,
                acao='alterado',
                titulo=f'Solicitação assumida pela TI: #{solicitacao.id}',
                descricao_extra='\n\nAção: Solicitação marcada como vista pela TI.'
            )

            sucesso = 'Solicitação assumida pela TI.'

        elif acao == 'iniciar_conversa':
            primeira_mensagem = request.POST.get('primeira_mensagem', '').strip()

            solicitacao.iniciar_conversa(request.user)
            solicitacao.atualizar_sla(salvar=True)

            if primeira_mensagem:
                MensagemSolicitacaoTI.objects.create(
                    solicitacao=solicitacao,
                    autor=request.user,
                    origem='ti',
                    mensagem=primeira_mensagem,
                    lida_pela_ti=True,
                    lida_pelo_solicitante=False,
                )
            else:
                MensagemSolicitacaoTI.objects.create(
                    solicitacao=solicitacao,
                    autor=request.user,
                    origem='sistema',
                    mensagem='A TI iniciou uma conversa com você nesta solicitação.',
                    lida_pela_ti=True,
                    lida_pelo_solicitante=False,
                )

            registrar_auditoria_solicitacao(
                request=request,
                solicitacao=solicitacao,
                acao='alterado',
                titulo=f'Conversa iniciada na solicitação: #{solicitacao.id}',
                descricao_extra=(
                    f'\n\nPrimeira mensagem:\n'
                    f'{primeira_mensagem or "A TI iniciou uma conversa com o solicitante."}'
                )
            )

            sucesso = 'Conversa iniciada com o solicitante.'

        elif acao == 'enviar_mensagem_ti':
            mensagem = request.POST.get('mensagem', '').strip()

            if not solicitacao.conversa_iniciada:
                erro = 'Inicie a conversa antes de enviar mensagens.'
            elif not mensagem:
                erro = 'Digite uma mensagem antes de enviar.'
            else:
                MensagemSolicitacaoTI.objects.create(
                    solicitacao=solicitacao,
                    autor=request.user,
                    origem='ti',
                    mensagem=mensagem,
                    lida_pela_ti=True,
                    lida_pelo_solicitante=False,
                )

                if solicitacao.status == 'aberto':
                    solicitacao.status = 'em_atendimento'
                    solicitacao.save()

                solicitacao.atualizar_sla(salvar=True)

                registrar_auditoria_solicitacao(
                    request=request,
                    solicitacao=solicitacao,
                    acao='alterado',
                    titulo=f'Mensagem da TI enviada na solicitação: #{solicitacao.id}',
                    descricao_extra=(
                        f'\n\nMensagem enviada pela TI:\n{mensagem}'
                    )
                )

                sucesso = 'Mensagem enviada ao solicitante.'

        elif acao == 'salvar_atendimento':
            status = request.POST.get('status', '').strip()
            prioridade = request.POST.get('prioridade', '').strip()
            resposta_ti = request.POST.get('resposta_ti', '').strip()

            if not status or not prioridade:
                erro = 'Preencha status e prioridade.'
            else:
                status_anterior = solicitacao.status
                prioridade_anterior = solicitacao.prioridade

                solicitacao.status = status
                solicitacao.prioridade = prioridade
                solicitacao.resposta_ti = resposta_ti
                solicitacao.visto_pela_ti = True

                if not solicitacao.visto_pela_ti_em:
                    solicitacao.visto_pela_ti_em = timezone.now()

                if not solicitacao.responsavel_ti:
                    solicitacao.responsavel_ti = request.user

                if status == 'resolvido':
                    solicitacao.resolvido_em = timezone.now()
                else:
                    solicitacao.resolvido_em = None

                solicitacao.sla_horas = SolicitacaoTI.obter_horas_sla_por_prioridade(prioridade)

                if solicitacao.criado_em:
                    solicitacao.sla_prazo_em = solicitacao.criado_em + timezone.timedelta(hours=solicitacao.sla_horas)

                solicitacao.save()
                solicitacao.atualizar_sla(salvar=True)

                if status != status_anterior:
                    MensagemSolicitacaoTI.objects.create(
                        solicitacao=solicitacao,
                        autor=request.user,
                        origem='sistema',
                        mensagem=f'Status da sua solicitação foi atualizado para: {solicitacao.get_status_display()}.',
                        lida_pela_ti=True,
                        lida_pelo_solicitante=False,
                    )

                registrar_auditoria_solicitacao(
                    request=request,
                    solicitacao=solicitacao,
                    acao='alterado',
                    titulo=f'Atendimento atualizado: #{solicitacao.id}',
                    descricao_extra=(
                        f'\n\nStatus anterior: {status_anterior}\n'
                        f'Status atual: {solicitacao.status}\n'
                        f'Prioridade anterior: {prioridade_anterior}\n'
                        f'Prioridade atual: {solicitacao.prioridade}\n'
                        f'SLA atual: {solicitacao.sla_status_exibicao}\n'
                        f'Resposta / tratativa da TI:\n{resposta_ti or "Não informada"}'
                    )
                )

                sucesso = 'Atendimento atualizado com sucesso.'

        elif acao == 'resolver':
            resposta_ti = request.POST.get('resposta_ti', '').strip()

            if not resposta_ti:
                erro = 'Informe a resposta ou solução aplicada antes de resolver.'
            else:
                solicitacao.resposta_ti = resposta_ti
                solicitacao.status = 'resolvido'
                solicitacao.resolvido_em = timezone.now()
                solicitacao.visto_pela_ti = True

                if not solicitacao.visto_pela_ti_em:
                    solicitacao.visto_pela_ti_em = timezone.now()

                if not solicitacao.responsavel_ti:
                    solicitacao.responsavel_ti = request.user

                solicitacao.save()
                solicitacao.atualizar_sla(salvar=True)

                MensagemSolicitacaoTI.objects.create(
                    solicitacao=solicitacao,
                    autor=request.user,
                    origem='sistema',
                    mensagem='Sua solicitação foi marcada como resolvida pela TI.',
                    lida_pela_ti=True,
                    lida_pelo_solicitante=False,
                )

                if solicitacao.conversa_iniciada:
                    MensagemSolicitacaoTI.objects.create(
                        solicitacao=solicitacao,
                        autor=request.user,
                        origem='ti',
                        mensagem=resposta_ti,
                        lida_pela_ti=True,
                        lida_pelo_solicitante=False,
                    )

                registrar_auditoria_solicitacao(
                    request=request,
                    solicitacao=solicitacao,
                    acao='encerrado',
                    titulo=f'Solicitação resolvida: #{solicitacao.id}',
                    descricao_extra=(
                        f'\n\nSolução aplicada:\n{resposta_ti}'
                    )
                )

                sucesso = 'Solicitação marcada como resolvida.'

        else:
            erro = 'Ação inválida.'

    MensagemSolicitacaoTI.objects.filter(
        solicitacao=solicitacao,
        origem='solicitante'
    ).update(
        lida_pela_ti=True
    )

    mensagens = solicitacao.mensagens.select_related(
        'autor'
    ).order_by(
        'criado_em'
    )

    return render(request, 'solicitacoes_ti/atender_solicitacao_ti.html', {
        'page_title': f'Atendimento #{solicitacao.id}',
        'solicitacao': solicitacao,
        'mensagens': mensagens,
        'status_choices': SolicitacaoTI.STATUS_CHOICES,
        'prioridades': SolicitacaoTI.PRIORIDADE_CHOICES,
        'erro': erro,
        'sucesso': sucesso,
    })
