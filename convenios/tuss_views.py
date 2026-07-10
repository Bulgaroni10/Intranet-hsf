from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from core.services.permissions import usuario_eh_admin_ti, usuario_pode_acessar_modulo_por_nome
from .models import ProcedimentoTUSS
from .services import buscar_procedimentos_tuss


NOME_MODULO_TUSS = 'Código TUSS'


@login_required(login_url='/')
def catalogo_tuss(request):
    if not usuario_pode_acessar_modulo_por_nome(request.user, NOME_MODULO_TUSS):
        return render(request, 'core/sem_permissao.html', status=403)

    busca = request.GET.get('busca', '').strip()
    grupo = request.GET.get('grupo', '').strip()
    pode_gerenciar = usuario_eh_admin_ti(request.user)
    procedimentos = buscar_procedimentos_tuss(
        busca=busca,
        grupo=grupo,
        incluir_inativos=pode_gerenciar and request.GET.get('inativos') == '1',
    )
    pagina = Paginator(procedimentos, 30).get_page(request.GET.get('pagina'))
    grupos = ProcedimentoTUSS.objects.filter(ativo=True).exclude(grupo='').values_list(
        'grupo', flat=True
    ).distinct().order_by('grupo')
    return render(request, 'convenios/catalogo_tuss.html', {
        'page_title': 'Código TUSS', 'pagina': pagina, 'busca': busca,
        'grupo': grupo, 'grupos': grupos, 'pode_gerenciar': pode_gerenciar,
        'total_procedimentos': ProcedimentoTUSS.objects.filter(ativo=True).count(),
    })
