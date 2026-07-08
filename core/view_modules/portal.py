from .common import *
from core.services.dashboard import montar_contexto_portal


@login_required(login_url="/")
def portal(request):
    contexto = montar_contexto_portal(request.user)

    return render(
        request,
        "core/portal.html",
        contexto
    )