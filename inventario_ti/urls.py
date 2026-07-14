from django.urls import path

from . import views


urlpatterns = [
    path("portal/modulos/inventario-ti/", views.dashboard, name="inventario_ti_dashboard"),
    path("portal/modulos/inventario-ti/exportar-csv/", views.exportar_inventario_csv, name="inventario_ti_exportar_csv"),
    path("portal/modulos/inventario-ti/erros-agentes/", views.erros_agentes, name="inventario_ti_erros_agentes"),
    path("portal/modulos/inventario-ti/erros-agentes/exportar-csv/", views.exportar_erros_agentes_csv, name="inventario_ti_erros_agentes_exportar_csv"),
    path("portal/modulos/inventario-ti/patrimonios/", views.patrimonios, name="inventario_ti_patrimonios"),
    path("portal/modulos/inventario-ti/patrimonios/novo/", views.novo_patrimonio, name="inventario_ti_patrimonio_novo"),
    path("portal/modulos/inventario-ti/patrimonios/importar/", views.importar_patrimonios, name="inventario_ti_patrimonios_importar"),
    path("portal/modulos/inventario-ti/patrimonios/modelo-importacao.csv", views.modelo_importacao_patrimonios, name="inventario_ti_patrimonios_modelo_importacao"),
    path("portal/modulos/inventario-ti/maquinas/", views.maquinas, name="inventario_ti_maquinas"),
    path("portal/modulos/inventario-ti/suprimentos/", views.suprimentos, name="inventario_ti_suprimentos"),
    path("portal/modulos/inventario-ti/suprimentos/novo/", views.novo_suprimento, name="inventario_ti_suprimento_novo"),
    path("portal/modulos/inventario-ti/suprimentos/<int:suprimento_id>/", views.detalhe_suprimento, name="inventario_ti_suprimento_detalhe"),
    path("portal/modulos/inventario-ti/suprimentos/<int:suprimento_id>/movimentar/", views.movimentar_suprimento, name="inventario_ti_suprimento_movimentar"),
    path("portal/modulos/inventario-ti/suprimentos/<int:suprimento_id>/movimentacoes/<int:movimentacao_id>/estornar/", views.estornar_movimentacao_suprimento, name="inventario_ti_suprimento_estornar"),
    path("portal/estoque-setorial/", views.estoque_setorial, name="estoque_setorial"),
    path("portal/estoque-setorial/novo/", views.novo_suprimento_setorial, name="estoque_setorial_novo"),
    path("portal/estoque-setorial/<int:suprimento_id>/", views.detalhe_suprimento, name="estoque_setorial_detalhe"),
    path("portal/estoque-setorial/<int:suprimento_id>/movimentar/", views.movimentar_suprimento, name="estoque_setorial_movimentar"),
    path("portal/estoque-setorial/<int:suprimento_id>/movimentacoes/<int:movimentacao_id>/estornar/", views.estornar_movimentacao_suprimento, name="estoque_setorial_estornar"),
    path("portal/suprimentos/anexos/<int:anexo_id>/", views.baixar_anexo_movimentacao_suprimento, name="suprimento_movimentacao_anexo"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/movimentar/", views.movimentar_patrimonio, name="inventario_ti_patrimonio_movimentar"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/", views.detalhe_patrimonio, name="inventario_ti_patrimonio_detalhe"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/editar/", views.editar_patrimonio, name="inventario_ti_patrimonio_editar"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/qr.svg", views.qr_patrimonio, name="inventario_ti_patrimonio_qr"),
    path("portal/modulos/inventario-ti/patrimonios/<int:patrimonio_id>/etiqueta/", views.etiqueta_patrimonio, name="inventario_ti_patrimonio_etiqueta"),
    path("portal/modulos/inventario-ti/<int:computador_id>/", views.detalhe, name="inventario_ti_detalhe"),

    path("api/heartbeat/", views.heartbeat, name="inventario_ti_heartbeat_compat"),
    path("api/inventario/heartbeat/", views.heartbeat, name="inventario_ti_heartbeat"),
    path("api/inventario/agent-error/", views.agent_error, name="inventario_ti_agent_error"),
]
