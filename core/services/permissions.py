from django.contrib.auth.decorators import user_passes_test


def usuario_tem_permissao(usuario, permissao):
    if not usuario or not usuario.is_authenticated:
        return False

    if usuario.is_superuser:
        return True

    return usuario.has_perm(permissao)


def permissao_requerida(permissao):
    return user_passes_test(
        lambda user: usuario_tem_permissao(user, permissao),
        login_url="/portal/sem-permissao/"
    )