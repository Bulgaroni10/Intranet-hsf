from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import ConversaChat, MensagemChat


def usuario_nome(usuario):
    nome = usuario.get_full_name()

    if nome:
        return nome

    return usuario.username


def usuario_descricao(usuario):
    partes = []

    if getattr(usuario, 'setor', None):
        partes.append(usuario.setor.nome)

    if getattr(usuario, 'unidade', None):
        partes.append(usuario.unidade.sigla)

    if partes:
        return ' • '.join(partes)

    return usuario.email or usuario.username


def contar_conversas_nao_lidas(usuario):
    if not usuario.is_authenticated:
        return 0

    return MensagemChat.objects.filter(
        conversa__ativo=True,
        conversa__participantes=usuario,
    ).exclude(
        remetente=usuario
    ).exclude(
        lida_por=usuario
    ).values(
        'conversa_id'
    ).distinct().count()


def usuario_para_json(usuario):
    return {
        'id': usuario.id,
        'nome': usuario_nome(usuario),
        'username': usuario.username,
        'descricao': usuario_descricao(usuario),
        'email': usuario.email or '',
        'unidade': usuario.unidade.sigla if getattr(usuario, 'unidade', None) else '',
        'setor': usuario.setor.nome if getattr(usuario, 'setor', None) else '',
    }


def mensagem_para_json(mensagem, usuario_logado):
    remetente = mensagem.remetente

    return {
        'id': mensagem.id,
        'texto': mensagem.texto,
        'criado_em': timezone.localtime(mensagem.criado_em).strftime('%d/%m/%Y %H:%M'),
        'hora': timezone.localtime(mensagem.criado_em).strftime('%H:%M'),
        'minha': remetente_id_igual(mensagem, usuario_logado),
        'remetente': {
            'id': remetente.id,
            'nome': usuario_nome(remetente),
            'username': remetente.username,
        },
    }


def remetente_id_igual(mensagem, usuario):
    return mensagem.remetente_id == usuario.id


def conversa_para_json(conversa, usuario_logado):
    participantes = list(conversa.participantes.exclude(id=usuario_logado.id))
    outro_usuario = participantes[0] if participantes else usuario_logado

    ultima_mensagem = conversa.mensagens.order_by('-criado_em').first()

    nao_lidas = conversa.mensagens.exclude(
        remetente=usuario_logado
    ).exclude(
        lida_por=usuario_logado
    ).count()

    return {
        'id': conversa.id,
        'usuario': usuario_para_json(outro_usuario),
        'ultima_mensagem': ultima_mensagem.texto if ultima_mensagem else '',
        'ultima_mensagem_hora': timezone.localtime(ultima_mensagem.criado_em).strftime('%H:%M') if ultima_mensagem else '',
        'nao_lidas': nao_lidas,
        'atualizado_em': timezone.localtime(conversa.atualizado_em).strftime('%d/%m/%Y %H:%M'),
    }


@login_required(login_url='/login/')
def conversas_home(request):
    User = get_user_model()

    usuarios = User.objects.filter(
        is_active=True
    ).exclude(
        id=request.user.id
    ).select_related(
        'unidade',
        'setor'
    ).order_by(
        'first_name',
        'last_name',
        'username'
    )

    return render(request, 'conversas/conversas_home.html', {
        'usuarios': usuarios,
    })


@login_required(login_url='/login/')
@require_GET
def contador_mensagens_nao_lidas(request):
    total = contar_conversas_nao_lidas(request.user)

    return JsonResponse({
        'ok': True,
        'total': total,
    })


@login_required(login_url='/login/')
@require_GET
def api_listar_conversas(request):
    conversas = ConversaChat.objects.filter(
        ativo=True,
        participantes=request.user
    ).prefetch_related(
        'participantes',
        'mensagens',
        'mensagens__remetente',
        'mensagens__lida_por',
    ).order_by(
        '-atualizado_em'
    )

    dados = [
        conversa_para_json(conversa, request.user)
        for conversa in conversas
    ]

    return JsonResponse({
        'ok': True,
        'conversas': dados,
        'total_nao_lidas': contar_conversas_nao_lidas(request.user),
    })


@login_required(login_url='/login/')
@require_POST
def api_iniciar_conversa(request):
    usuario_id = request.POST.get('usuario_id')

    if not usuario_id:
        return JsonResponse({
            'ok': False,
            'message': 'Usuário não informado.'
        }, status=400)

    User = get_user_model()

    usuario_destino = get_object_or_404(
        User.objects.filter(is_active=True),
        id=usuario_id
    )

    if usuario_destino.id == request.user.id:
        return JsonResponse({
            'ok': False,
            'message': 'Você não pode iniciar conversa com você mesmo.'
        }, status=400)

    conversa = ConversaChat.objects.filter(
        ativo=True,
        participantes=request.user
    ).filter(
        participantes=usuario_destino
    ).distinct().first()

    if not conversa:
        conversa = ConversaChat.objects.create(
            ativo=True
        )

        conversa.participantes.add(request.user)
        conversa.participantes.add(usuario_destino)

    return JsonResponse({
        'ok': True,
        'conversa': conversa_para_json(conversa, request.user),
    })


@login_required(login_url='/login/')
@require_GET
def api_mensagens_conversa(request, conversa_id):
    conversa = get_object_or_404(
        ConversaChat.objects.filter(
            ativo=True,
            participantes=request.user
        ).prefetch_related(
            'participantes',
            'mensagens',
            'mensagens__remetente',
            'mensagens__lida_por',
        ),
        id=conversa_id
    )

    mensagens_nao_lidas = conversa.mensagens.exclude(
        remetente=request.user
    ).exclude(
        lida_por=request.user
    )

    for mensagem in mensagens_nao_lidas:
        mensagem.lida_por.add(request.user)

    mensagens = conversa.mensagens.select_related(
        'remetente'
    ).order_by(
        'criado_em'
    )

    return JsonResponse({
        'ok': True,
        'conversa': conversa_para_json(conversa, request.user),
        'mensagens': [
            mensagem_para_json(mensagem, request.user)
            for mensagem in mensagens
        ],
        'total_nao_lidas': contar_conversas_nao_lidas(request.user),
    })


@login_required(login_url='/login/')
@require_POST
def api_enviar_mensagem(request):
    conversa_id = request.POST.get('conversa_id')
    texto = request.POST.get('texto', '').strip()

    if not conversa_id:
        return JsonResponse({
            'ok': False,
            'message': 'Conversa não informada.'
        }, status=400)

    if not texto:
        return JsonResponse({
            'ok': False,
            'message': 'Digite uma mensagem antes de enviar.'
        }, status=400)

    conversa = get_object_or_404(
        ConversaChat.objects.filter(
            ativo=True,
            participantes=request.user
        ),
        id=conversa_id
    )

    mensagem = MensagemChat.objects.create(
        conversa=conversa,
        remetente=request.user,
        texto=texto
    )

    mensagem.lida_por.add(request.user)

    return JsonResponse({
        'ok': True,
        'mensagem': mensagem_para_json(mensagem, request.user),
        'conversa': conversa_para_json(conversa, request.user),
    })