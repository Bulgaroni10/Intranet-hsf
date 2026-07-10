from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.services.search import buscar_global


@login_required(login_url='/')
def busca_global(request):
    termo = request.GET.get('q', '').strip()
    resultados = buscar_global(request, termo) if termo else []
    return render(request, 'core/busca_global.html', {
        'page_title': 'Busca Global', 'termo': termo, 'resultados': resultados,
    })
