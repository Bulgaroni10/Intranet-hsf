from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json

from .models import ComputadorInventario


@csrf_exempt
def heartbeat(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método não permitido"}, status=405)

    try:
        dados = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido"}, status=400)

    hostname = dados.get("hostname", "").strip().upper()

    if not hostname:
        return JsonResponse({"ok": False, "erro": "Hostname obrigatório"}, status=400)

    ip_origem = request.META.get("REMOTE_ADDR")

    computador, criado = ComputadorInventario.objects.update_or_create(
        hostname=hostname,
        defaults={
            "usuario": dados.get("usuario") or "-",
            "ip_origem": ip_origem,
            "ip_local": dados.get("ip_local") or None,
            "mac": dados.get("mac") or "-",
            "sistema": dados.get("sistema") or "-",
            "cpu": dados.get("cpu") or "-",
            "ram": dados.get("ram") or "-",
            "disco_total": dados.get("disco_total") or "-",
            "disco_livre": dados.get("disco_livre") or "-",
            "disco_percentual": dados.get("disco_percentual") or "-",
            "fabricante": dados.get("fabricante") or "-",
            "modelo": dados.get("modelo") or "-",
            "serial": dados.get("serial") or "-",
            "agent_version": dados.get("agent_version") or "-",
            "ultimo_contato": timezone.now(),
        }
    )

    return JsonResponse({
        "ok": True,
        "criado": criado,
        "hostname": computador.hostname,
        "status": computador.status_texto,
    })


@login_required
def dashboard(request):
    busca = request.GET.get("busca", "").strip()

    computadores = ComputadorInventario.objects.all()

    if busca:
        computadores = computadores.filter(
            Q(hostname__icontains=busca) |
            Q(usuario__icontains=busca) |
            Q(ip_local__icontains=busca) |
            Q(mac__icontains=busca) |
            Q(serial__icontains=busca) |
            Q(modelo__icontains=busca) |
            Q(patrimonio__icontains=busca)
        )

    lista = list(computadores)

    total = len(lista)
    online = len([pc for pc in lista if pc.online])
    offline = total - online
    sem_patrimonio = len([pc for pc in lista if not pc.patrimonio or pc.patrimonio == "-"])

    paginator = Paginator(lista, 20)
    pagina = request.GET.get("page")
    computadores_pagina = paginator.get_page(pagina)

    return render(request, "inventario_ti/dashboard.html", {
        "computadores": computadores_pagina,
        "busca": busca,
        "totais": {
            "total": total,
            "online": online,
            "offline": offline,
            "sem_patrimonio": sem_patrimonio,
        }
    })


@login_required
def detalhe(request, computador_id):
    computador = get_object_or_404(ComputadorInventario, id=computador_id)

    return render(request, "inventario_ti/detalhe.html", {
        "computador": computador
    })