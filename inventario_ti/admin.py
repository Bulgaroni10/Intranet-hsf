from django.contrib import admin

from .models import (
    ComputadorInventario,
    ErroAgenteInventario,
    HistoricoComputadorInventario,
    MovimentacaoPatrimonioTI,
    PatrimonioTI,
    ImpressoraMonitorada,
    MonitoramentoActiveDirectory,
    MonitoramentoServidor,
    MonitoramentoRede,
)


@admin.register(ComputadorInventario)
class ComputadorInventarioAdmin(admin.ModelAdmin):
    list_display = [
        "unidade",
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
        "unidade",
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
        "unidade",
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
        "unidade",
        "categoria",
        "agent_version",
        "criado_em",
    ]

    readonly_fields = [
        "computador",
        "unidade",
        "hostname",
        "agent_version",
        "categoria",
        "mensagem",
        "detalhe",
        "payload",
        "ip_origem",
        "criado_em",
    ]


@admin.register(PatrimonioTI)
class PatrimonioTIAdmin(admin.ModelAdmin):
    list_display = [
        "codigo",
        "tipo",
        "status",
        "computador",
        "unidade",
        "setor",
        "responsavel",
        "ativo",
        "atualizado_em",
    ]

    search_fields = [
        "codigo",
        "responsavel",
        "fabricante",
        "modelo",
        "serial",
        "nota_fiscal",
        "computador__hostname",
    ]

    list_filter = [
        "tipo",
        "status",
        "unidade",
        "setor",
        "ativo",
    ]

    readonly_fields = [
        "criado_em",
        "atualizado_em",
    ]


@admin.register(MovimentacaoPatrimonioTI)
class MovimentacaoPatrimonioTIAdmin(admin.ModelAdmin):
    list_display = [
        "patrimonio",
        "tipo",
        "unidade_origem",
        "unidade_destino",
        "usuario",
        "criado_em",
    ]

    search_fields = [
        "patrimonio__codigo",
        "responsavel_origem",
        "responsavel_destino",
        "observacao",
    ]

    list_filter = [
        "tipo",
        "unidade_origem",
        "unidade_destino",
        "criado_em",
    ]


@admin.register(ImpressoraMonitorada)
class ImpressoraMonitoradaAdmin(admin.ModelAdmin):
    list_display = ["local", "ip", "modelo_detectado", "unidade", "online", "status_dispositivo", "ultima_consulta"]
    search_fields = ["local", "ip", "modelo_informado", "modelo_detectado"]
    list_filter = ["unidade", "online", "ativo"]
    readonly_fields = ["modelo_detectado", "online", "status_dispositivo", "toner_percentual", "cilindro_percentual", "ultimo_erro", "ultima_consulta", "criado_em", "atualizado_em"]


@admin.register(MonitoramentoActiveDirectory)
class MonitoramentoActiveDirectoryAdmin(admin.ModelAdmin):
    list_display = ["controlador", "ip", "online", "ldap_ok", "kerberos_ok", "dns_ok", "smb_ok", "latencia_ms", "ultima_consulta"]
    readonly_fields = ["ip", "online", "ldap_ok", "kerberos_ok", "dns_ok", "smb_ok", "latencia_ms", "detalhe", "ultima_consulta", "atualizado_em"]


@admin.register(MonitoramentoServidor)
class MonitoramentoServidorAdmin(admin.ModelAdmin):
    list_display = ["hostname", "ip", "cpu_percentual", "memoria_percentual", "disco_percentual", "disco_livre_gb", "ultima_consulta"]
    readonly_fields = ["hostname", "ip", "cpu_percentual", "memoria_percentual", "memoria_total_gb", "disco_percentual", "disco_livre_gb", "uptime_segundos", "detalhe", "ultima_consulta", "atualizado_em"]


@admin.register(MonitoramentoRede)
class MonitoramentoRedeAdmin(admin.ModelAdmin):
    list_display = ["nome", "gateway_ok", "dns_ok", "switch_ok", "switch_modelo", "switch_interfaces", "ultima_consulta"]
    readonly_fields = ["gateway_ok", "dns_ok", "switch_ok", "switch_modelo", "switch_uptime_segundos", "switch_interfaces", "detalhe", "ultima_consulta", "atualizado_em"]
