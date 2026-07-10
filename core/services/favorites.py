from core.models import FavoritoModulo
from core.services.permissions import usuario_pode_acessar_modulo


def listar_favoritos(usuario):
    favoritos = FavoritoModulo.objects.filter(
        usuario=usuario,
        modulo__ativo=True,
    ).select_related('modulo')
    return [item for item in favoritos if usuario_pode_acessar_modulo(usuario, item.modulo)]


def alternar_favorito(usuario, modulo):
    if not modulo.ativo or not usuario_pode_acessar_modulo(usuario, modulo):
        raise PermissionError('Módulo não autorizado para este usuário.')

    favorito = FavoritoModulo.objects.filter(usuario=usuario, modulo=modulo).first()
    if favorito:
        favorito.delete()
        return False

    FavoritoModulo.objects.create(usuario=usuario, modulo=modulo)
    return True
