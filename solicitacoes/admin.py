from django.contrib import admin

from .models import (
    CategoriaSolicitacao,
    SolicitacaoInterna,
    ComentarioSolicitacao,
)


@admin.register(CategoriaSolicitacao)
class CategoriaSolicitacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome', 'descricao']


class ComentarioSolicitacaoInline(admin.TabularInline):
    model = ComentarioSolicitacao
    extra = 0
    readonly_fields = ['criado_em']


@admin.register(SolicitacaoInterna)
class SolicitacaoInternaAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'titulo',
        'categoria',
        'solicitante',
        'responsavel',
        'status',
        'prioridade',
        'criado_em',
    ]

    list_filter = [
        'status',
        'prioridade',
        'categoria',
        'unidade',
        'setor',
        'criado_em',
    ]

    search_fields = [
        'id',
        'titulo',
        'descricao',
        'solicitante__username',
        'solicitante__first_name',
        'solicitante__last_name',
    ]

    readonly_fields = [
        'criado_em',
        'atualizado_em',
        'concluido_em',
    ]

    inlines = [ComentarioSolicitacaoInline]


@admin.register(ComentarioSolicitacao)
class ComentarioSolicitacaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'solicitacao', 'autor', 'criado_em']
    search_fields = ['mensagem', 'autor__username']
    list_filter = ['criado_em']