from django.contrib import admin

from .models import ComputadorInventario


@admin.register(ComputadorInventario)
class ComputadorInventarioAdmin(admin.ModelAdmin):
    list_display = [
        "hostname",
        "usuario",
        "ip_local",
        "mac",
        "sistema",
        "ram",
        "disco_livre",
        "disco_percentual",
        "fabricante",
        "modelo",
        "serial",
        "agent_version",
        "ultimo_contato",
    ]

    search_fields = [
        "hostname",
        "usuario",
        "ip_local",
        "mac",
        "serial",
        "modelo",
        "patrimonio",
    ]

    list_filter = [
        "fabricante",
        "sistema",
        "agent_version",
        "ultimo_contato",
    ]

    readonly_fields = [
        "criado_em",
        "atualizado_em",
        "ultimo_contato",
    ]