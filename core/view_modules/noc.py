from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.services.noc import montar_contexto_noc
from core.services.permissions import usuario_eh_ti


@login_required(login_url='/')
def painel_noc(request):
    if not usuario_eh_ti(request.user):
        return render(request, 'core/sem_permissao.html', status=403)
    return render(request, 'core/noc.html', montar_contexto_noc(request.user))
