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


@login_required(login_url="/")
def sidebar_global(request):
    """Entrega sidebar e topbar do portal às telas legadas autenticadas."""
    return render(request, "partials/legacy_chrome.html")
