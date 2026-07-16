from django.urls import path
from . import views

urlpatterns = [
    path('portal/financeiro-faturamento/', views.lista, name='financeiro_lista'),
    path('portal/financeiro-faturamento/novo/', views.editar, name='financeiro_novo'),
    path('portal/financeiro-faturamento/<int:registro_id>/', views.detalhe, name='financeiro_detalhe'),
    path('portal/financeiro-faturamento/<int:registro_id>/editar/', views.editar, name='financeiro_editar'),
    path('portal/financeiro-faturamento/anexos/<int:anexo_id>/', views.baixar_anexo, name='financeiro_anexo'),
]
