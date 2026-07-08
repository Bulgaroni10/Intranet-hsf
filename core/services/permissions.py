from django.contrib.auth.decorators import user_passes_test


PERFIS_TI = ("TI Administrador", "TI Suporte", "TI")
PERFIS_GESTAO = ("Gestão", "Gerência", "Diretoria", "Responsável Técnico")


def usuario_pertence_a_algum_grupo(usuario, nomes_grupos):
    if not usuario or not usuario.is_authenticated:
        return False

    return usuario.groups.filter(name__in=nomes_grupos).exists()


def usuario_eh_admin_ti(usuario):
    if not usuario or not usuario.is_authenticated:
        return False

    return usuario.is_superuser or usuario_pertence_a_algum_grupo(usuario, ("TI Administrador",))


def usuario_eh_ti(usuario):
    return usuario_eh_admin_ti(usuario) or usuario_pertence_a_algum_grupo(usuario, PERFIS_TI)


def usuario_eh_gestao(usuario):
    return usuario_pertence_a_algum_grupo(usuario, PERFIS_GESTAO)


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
