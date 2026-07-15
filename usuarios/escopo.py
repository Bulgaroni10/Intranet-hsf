from django.db.models import Q


def obter_unidade_ativa(user):
    """Retorna a unidade atualmente selecionada para o usuário."""
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'unidade', None)


def aplicar_escopo_unidade(
    queryset,
    user,
    *,
    campo='unidade',
    incluir_globais=False,
    campos_compartilhados=(),
):
    """Restringe dados à unidade ativa, inclusive para administradores.

    Registros globais e relações de compartilhamento precisam ser solicitados
    explicitamente. Sem unidade ativa, o retorno padrão é vazio.
    """
    unidade = obter_unidade_ativa(user)
    if unidade is None:
        if incluir_globais:
            return queryset.filter(**{f'{campo}__isnull': True})
        return queryset.none()

    regra = Q(**{campo: unidade})
    if incluir_globais:
        regra |= Q(**{f'{campo}__isnull': True})
    for compartilhado in campos_compartilhados:
        regra |= Q(**{compartilhado: unidade})
    return queryset.filter(regra).distinct()
