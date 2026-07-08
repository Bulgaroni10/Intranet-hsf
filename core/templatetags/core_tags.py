from django import template

from core.services.permissions import (
    usuario_eh_admin_ti,
    usuario_eh_ti,
    usuario_eh_gestao,
    usuario_pode_acessar_administracao,
    usuario_pode_acessar_inventario_ti,
    usuario_pode_acessar_modulo_por_link,
    usuario_pode_acessar_modulo_por_nome,
    usuario_pode_acessar_solicitacoes_ti,
    usuario_pode_ver_dashboard_gestao,
    usuario_pode_ver_painel_tecnico,
)


register = template.Library()


@register.simple_tag
def usuario_eh_admin_ti_tag(user):
    return usuario_eh_admin_ti(user)


@register.simple_tag
def usuario_eh_ti_tag(user):
    return usuario_eh_ti(user)


@register.simple_tag
def usuario_eh_gestao_tag(user):
    return usuario_eh_gestao(user)


@register.simple_tag
def usuario_pode_ver_painel_tecnico_tag(user):
    return usuario_pode_ver_painel_tecnico(user)


@register.simple_tag
def usuario_pode_ver_dashboard_gestao_tag(user):
    return usuario_pode_ver_dashboard_gestao(user)


@register.simple_tag
def usuario_pode_ver_inventario_ti(user):
    return usuario_pode_acessar_inventario_ti(user)


@register.simple_tag
def usuario_pode_acessar_administracao_tag(user):
    return usuario_pode_acessar_administracao(user)


@register.simple_tag
def usuario_pode_acessar_solicitacoes_ti_tag(user):
    return usuario_pode_acessar_solicitacoes_ti(user)


@register.simple_tag
def pode_acessar_modulo_link(user, link_modulo):
    return usuario_pode_acessar_modulo_por_link(user, link_modulo)


@register.simple_tag
def pode_acessar_modulo_nome(user, nome_modulo):
    return usuario_pode_acessar_modulo_por_nome(user, nome_modulo)