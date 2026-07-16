from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from core.models import NotificacaoUsuario
from core.services.notifications import (
    contar_nao_lidas,
    listar_notificacoes,
    marcar_como_lida,
    marcar_todas_como_lidas,
)


def _serializar(notificacao):
    return {
        'id': notificacao.id,
        'titulo': notificacao.titulo,
        'descricao': notificacao.descricao,
        'tipo': notificacao.tipo,
        'icone': notificacao.icone,
        'link': notificacao.link,
        'lida': notificacao.lida,
        'criado_em': notificacao.criado_em.isoformat(),
        'atualizado_em': notificacao.atualizado_em.isoformat(),
    }


@login_required(login_url='/')
@require_GET
def api_listar_notificacoes(request):
    itens = listar_notificacoes(request.user, limite=30, unidade=request.user.unidade)
    return JsonResponse({
        'notificacoes': [_serializar(item) for item in itens],
        'nao_lidas': contar_nao_lidas(request.user, unidade=request.user.unidade),
    })


@login_required(login_url='/')
@require_POST
def api_marcar_notificacao_lida(request, notificacao_id):
    get_object_or_404(
        NotificacaoUsuario.objects.filter(Q(unidade=request.user.unidade) | Q(unidade__isnull=True)),
        id=notificacao_id, usuario=request.user,
    )
    marcar_como_lida(request.user, notificacao_id, unidade=request.user.unidade)
    return JsonResponse({'ok': True, 'nao_lidas': contar_nao_lidas(request.user, unidade=request.user.unidade)})


@login_required(login_url='/')
@require_POST
def api_marcar_todas_notificacoes_lidas(request):
    marcar_todas_como_lidas(request.user, unidade=request.user.unidade)
    return JsonResponse({'ok': True, 'nao_lidas': 0})
