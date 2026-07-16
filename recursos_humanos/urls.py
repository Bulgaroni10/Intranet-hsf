from django.urls import path

from . import views


urlpatterns = [
    path('portal/recursos-humanos/', views.lista, name='rh_lista'),
    path('portal/recursos-humanos/nova/', views.nova, name='rh_nova'),
    path('portal/recursos-humanos/<int:solicitacao_id>/', views.detalhe, name='rh_detalhe'),
    path('portal/recursos-humanos/<int:solicitacao_id>/atender/', views.atender, name='rh_atender'),
    path('portal/recursos-humanos/anexos/<int:anexo_id>/', views.baixar_anexo, name='rh_anexo'),
]
