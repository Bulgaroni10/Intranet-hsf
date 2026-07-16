from django.urls import path

from . import views


urlpatterns = [
    path('portal/gestao-acessos/', views.lista, name='gestao_acessos_lista'),
    path('portal/gestao-acessos/nova/', views.nova, name='gestao_acessos_nova'),
    path('portal/gestao-acessos/<int:solicitacao_id>/', views.detalhe, name='gestao_acessos_detalhe'),
    path('portal/gestao-acessos/<int:solicitacao_id>/atender/', views.atender, name='gestao_acessos_atender'),
    path('portal/gestao-acessos/anexos/<int:anexo_id>/', views.baixar_anexo, name='gestao_acessos_anexo'),
]
