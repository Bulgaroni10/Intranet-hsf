from core.services.favorites import listar_favoritos
from core.services.notifications import contar_nao_lidas, listar_notificacoes


def contexto_usuario_gsf(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'favoritos_usuario': listar_favoritos(request.user),
        'notificacoes': listar_notificacoes(request.user),
        'total_notificacoes': contar_nao_lidas(request.user),
    }
