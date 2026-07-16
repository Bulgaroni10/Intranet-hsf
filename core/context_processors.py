from core.services.favorites import listar_favoritos
from core.services.notifications import contar_nao_lidas, listar_notificacoes
from usuarios.models import Unidade


def contexto_usuario_gsf(request):
    if not request.user.is_authenticated:
        return {}
    unidades_disponiveis = list(
        request.user.unidades_permitidas.filter(ativo=True).order_by('nome')
    )
    if not unidades_disponiveis and request.user.unidade_id:
        unidades_disponiveis = list(
            Unidade.objects.filter(id=request.user.unidade_id, ativo=True)
        )

    return {
        'favoritos_usuario': listar_favoritos(request.user),
        'notificacoes': listar_notificacoes(request.user, unidade=request.user.unidade),
        'total_notificacoes': contar_nao_lidas(request.user, unidade=request.user.unidade),
        'unidades_disponiveis_usuario': unidades_disponiveis,
    }
