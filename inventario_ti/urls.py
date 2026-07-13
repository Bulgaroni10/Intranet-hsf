from django.urls import path

from . import views


urlpatterns = [
    path("portal/modulos/inventario-ti/", views.dashboard, name="inventario_ti_dashboard"),
    path("portal/modulos/inventario-ti/exportar-csv/", views.exportar_inventario_csv, name="inventario_ti_exportar_csv"),
    path("portal/modulos/inventario-ti/erros-agentes/", views.erros_agentes, name="inventario_ti_erros_agentes"),
    path("portal/modulos/inventario-ti/erros-agentes/exportar-csv/", views.exportar_erros_agentes_csv, name="inventario_ti_erros_agentes_exportar_csv"),
    path("portal/modulos/inventario-ti/patrimonios/", views.patrimonios, name="inventario_ti_patrimonios"),
    path("portal/modulos/inventario-ti/patrimonios/novo/", views.novo_patrimonio, name="inventario_ti_patrimonio_novo"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/", views.detalhe_patrimonio, name="inventario_ti_patrimonio_detalhe"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/editar/", views.editar_patrimonio, name="inventario_ti_patrimonio_editar"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/qr.svg", views.qr_patrimonio, name="inventario_ti_patrimonio_qr"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/etiqueta/", views.etiqueta_patrimonio, name="inventario_ti_patrimonio_etiqueta"),
    path("portal/modulos/inventario-ti/<int:computador_id>/", views.detalhe, name="inventario_ti_detalhe"),

    path("api/heartbeat/", views.heartbeat, name="inventario_ti_heartbeat_compat"),
    path("api/inventario/heartbeat/", views.heartbeat, name="inventario_ti_heartbeat"),
    path("api/inventario/agent-error/", views.agent_error, name="inventario_ti_agent_error"),
]
