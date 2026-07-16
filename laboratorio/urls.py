from django.urls import path
from . import views

urlpatterns = [
    path('portal/laboratorio/', views.lista, name='laboratorio_lista'),
    path('portal/laboratorio/novo/', views.editar, name='laboratorio_novo'),
    path('portal/laboratorio/<int:exame_id>/', views.detalhe, name='laboratorio_detalhe'),
    path('portal/laboratorio/<int:exame_id>/editar/', views.editar, name='laboratorio_editar'),
    path('portal/laboratorio/documentos/<int:documento_id>/', views.baixar_documento, name='laboratorio_documento'),
]
