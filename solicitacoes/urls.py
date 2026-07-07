from django.urls import path

from . import views


urlpatterns = [
    path(
        'portal/modulos/solicitacoes/',
        views.solicitacoes_home,
        name='solicitacoes_home'
    ),
    path(
        'portal/modulos/solicitacoes/nova/',
        views.nova_solicitacao,
        name='nova_solicitacao'
    ),
    path(
        'portal/modulos/solicitacoes/<int:solicitacao_id>/',
        views.detalhe_solicitacao,
        name='detalhe_solicitacao'
    ),
    path(
        'portal/modulos/solicitacoes/<int:solicitacao_id>/atender/',
        views.atender_solicitacao,
        name='atender_solicitacao'
    ),
]