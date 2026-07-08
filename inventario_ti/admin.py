from django.contrib import admin

from .models import ComputadorInventario, ErroAgenteInventario, HistoricoComputadorInventario


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


@admin.register(HistoricoComputadorInventario)
class HistoricoComputadorInventarioAdmin(admin.ModelAdmin):
    list_display = [
        "computador",
        "tipo",
        "titulo",
        "campo",
        "criado_em",
    ]

    search_fields = [
        "computador__hostname",
        "titulo",
        "descricao",
        "campo",
        "valor_anterior",
        "valor_novo",
    ]

    list_filter = [
        "tipo",
        "campo",
        "criado_em",
    ]

    readonly_fields = [
        "computador",
        "tipo",
        "titulo",
        "descricao",
        "campo",
        "valor_anterior",
        "valor_novo",
        "dados",
        "criado_em",
    ]


@admin.register(ErroAgenteInventario)
class ErroAgenteInventarioAdmin(admin.ModelAdmin):
    list_display = [
        "hostname",
        "agent_version",
        "categoria",
        "ip_origem",
        "criado_em",
    ]

    search_fields = [
        "hostname",
        "agent_version",
        "categoria",
        "mensagem",
        "detalhe",
    ]

    list_filter = [
        "categoria",
        "agent_version",
        "criado_em",
    ]

    readonly_fields = [
        "computador",
        "hostname",
        "agent_version",
        "categoria",
        "mensagem",
        "detalhe",
        "payload",
        "ip_origem",
        "criado_em",
    ]
