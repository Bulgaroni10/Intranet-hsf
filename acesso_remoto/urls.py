from django.urls import path

from . import views


urlpatterns = [
    path('portal/acesso-remoto/', views.lista, name='acesso_remoto_lista'),
    path('portal/acesso-remoto/nova/', views.nova, name='acesso_remoto_nova'),
    path('portal/acesso-remoto/<int:solicitacao_id>/', views.detalhe, name='acesso_remoto_detalhe'),
    path('portal/acesso-remoto/<int:solicitacao_id>/atender/', views.atender, name='acesso_remoto_atender'),
    path('portal/acesso-remoto/anexos/<int:anexo_id>/', views.baixar_anexo, name='acesso_remoto_anexo'),
]
