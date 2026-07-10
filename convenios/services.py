from django.db.models import Q

from .models import ProcedimentoTUSS


def buscar_procedimentos_tuss(*, busca='', grupo='', incluir_inativos=False):
    procedimentos = ProcedimentoTUSS.objects.all()
    if not incluir_inativos:
        procedimentos = procedimentos.filter(ativo=True)
    if busca:
        procedimentos = procedimentos.filter(
            Q(codigo_tuss__icontains=busca)
            | Q(descricao__icontains=busca)
            | Q(codigo_mv__icontains=busca)
            | Q(grupo__icontains=busca)
        )
    if grupo:
        procedimentos = procedimentos.filter(grupo=grupo)
    return procedimentos.order_by('descricao', 'codigo_tuss')
