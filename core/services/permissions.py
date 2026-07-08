from django.contrib.auth.decorators import user_passes_test

from modulos.models import Modulo


PERFIS_TI = (
    "TI Administrador",
    "TI Suporte",
    "TI",
)

PERFIS_GESTAO = (
    "Gestão",
    "Gestao",
    "Gerência",
    "Gerencia",
    "Diretoria",
    "Responsável Técnico",
    "Responsavel Tecnico",
)


def usuario_autenticado(user):
    return bool(user and user.is_authenticated)


def usuario_pertence_a_algum_grupo(user, nomes_grupos):
    if not usuario_autenticado(user):
        return False

    return user.groups.filter(name__in=nomes_grupos).exists()


def usuario_eh_admin(user):
    if not usuario_autenticado(user):
        return False

    return user.is_superuser


def usuario_eh_admin_ti(user):
    if not usuario_autenticado(user):
        return False

    return user.is_superuser or usuario_pertence_a_algum_grupo(
        user,
        ("TI Administrador",)
    )


def usuario_eh_ti(user):
    if not usuario_autenticado(user):
        return False

    return usuario_eh_admin_ti(user) or usuario_pertence_a_algum_grupo(
        user,
        PERFIS_TI
    )


def usuario_eh_gestao(user):
    if not usuario_autenticado(user):
        return False

    return usuario_pertence_a_algum_grupo(
        user,
        PERFIS_GESTAO
    )


def usuario_eh_usuario_comum(user):
    if not usuario_autenticado(user):
        return False

    return not usuario_eh_ti(user) and not usuario_eh_gestao(user)


def usuario_pode_ver_painel_tecnico(user):
    return usuario_eh_ti(user)


def usuario_pode_ver_dashboard_gestao(user):
    return usuario_eh_admin_ti(user) or usuario_eh_gestao(user)


def usuario_pode_acessar_administracao(user):
    return usuario_eh_admin_ti(user)


def usuario_pode_acessar_inventario_ti(user):
    return usuario_eh_ti(user)


def usuario_pode_acessar_modulo_por_nome(user, nome_modulo):
    if not usuario_autenticado(user):
        return False

    if usuario_eh_admin_ti(user):
        return True

    try:
        modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    except Modulo.DoesNotExist:
        return False

    if not modulo.grupos_permitidos.exists():
        return True

    return modulo.grupos_permitidos.filter(
        id__in=user.groups.values_list("id", flat=True)
    ).exists()


def usuario_pode_acessar_modulo_por_link(user, link_modulo):
    if not usuario_autenticado(user):
        return False

    if usuario_eh_admin_ti(user):
        return True

    try:
        modulo = Modulo.objects.get(link=link_modulo, ativo=True)
    except Modulo.DoesNotExist:
        return False

    if not modulo.grupos_permitidos.exists():
        return True

    return modulo.grupos_permitidos.filter(
        id__in=user.groups.values_list("id", flat=True)
    ).exists()


def usuario_pode_acessar_modulo(user, modulo_ou_nome):
    if isinstance(modulo_ou_nome, Modulo):
        return usuario_pode_acessar_modulo_por_nome(
            user,
            modulo_ou_nome.nome
        )

    return usuario_pode_acessar_modulo_por_nome(
        user,
        modulo_ou_nome
    )


def usuario_pode_acessar_solicitacoes_ti(user):
    if not usuario_autenticado(user):
        return False

    if usuario_eh_ti(user):
        return True

    links_possiveis = (
        "/portal/modulos/solicitacoes-ti/",
        "/portal/modulos/solicitacoes-ti",
    )

    nomes_possiveis = (
        "Solicitações de TI",
        "Solicitações Internas de TI",
        "Solicitações TI",
        "Chamados de TI",
    )

    for link in links_possiveis:
        if usuario_pode_acessar_modulo_por_link(user, link):
            return True

    for nome in nomes_possiveis:
        if usuario_pode_acessar_modulo_por_nome(user, nome):
            return True

    return False


def usuario_tem_permissao(user, permissao):
    if not usuario_autenticado(user):
        return False

    if user.is_superuser:
        return True

    return user.has_perm(permissao)


def permissao_requerida(permissao):
    return user_passes_test(
        lambda user: usuario_tem_permissao(user, permissao),
        login_url="/portal/sem-permissao/"
    )


def ti_requerido():
    return user_passes_test(
        usuario_eh_ti,
        login_url="/portal/sem-permissao/"
    )


def admin_ti_requerido():
    return user_passes_test(
        usuario_eh_admin_ti,
        login_url="/portal/sem-permissao/"
    )