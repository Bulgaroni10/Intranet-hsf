from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from modulos.models import Modulo
from core.services.favorites import alternar_favorito


@login_required(login_url='/')
@require_POST
def alternar_favorito_modulo(request, modulo_id):
    modulo = get_object_or_404(Modulo, id=modulo_id, ativo=True)
    try:
        ativo = alternar_favorito(request.user, modulo)
    except PermissionError:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'erro': 'Acesso negado.'}, status=403)
        return redirect('portal')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'favorito': ativo})
    return redirect(request.POST.get('next') or 'portal')
