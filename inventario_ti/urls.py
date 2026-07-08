from django.urls import path

from . import views


urlpatterns = [
    path("portal/modulos/inventario-ti/", views.dashboard, name="inventario_ti_dashboard"),
    path("portal/modulos/inventario-ti/<int:computador_id>/", views.detalhe, name="inventario_ti_detalhe"),

    path("api/heartbeat/", views.heartbeat, name="inventario_ti_heartbeat_compat"),
    path("api/inventario/heartbeat/", views.heartbeat, name="inventario_ti_heartbeat"),
]