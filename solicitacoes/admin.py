from django.contrib import admin

from .models import (
    CategoriaSolicitacao,
    SolicitacaoInterna,
    ComentarioSolicitacao,
    HistoricoSolicitacao,
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


class HistoricoSolicitacaoInline(admin.TabularInline):
    model = HistoricoSolicitacao
    extra = 0
    readonly_fields = [
        'usuario',
        'tipo',
        'titulo',
        'descricao',
        'valor_anterior',
        'valor_novo',
        'criado_em',
    ]

    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


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

    inlines = [
        ComentarioSolicitacaoInline,
        HistoricoSolicitacaoInline,
    ]


@admin.register(ComentarioSolicitacao)
class ComentarioSolicitacaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'solicitacao', 'autor', 'criado_em']
    search_fields = ['mensagem', 'autor__username']
    list_filter = ['criado_em']


@admin.register(HistoricoSolicitacao)
class HistoricoSolicitacaoAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'solicitacao',
        'usuario',
        'tipo',
        'titulo',
        'criado_em',
    ]

    list_filter = [
        'tipo',
        'criado_em',
    ]

    search_fields = [
        'solicitacao__id',
        'solicitacao__titulo',
        'titulo',
        'descricao',
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
    ]

    readonly_fields = [
        'solicitacao',
        'usuario',
        'tipo',
        'titulo',
        'descricao',
        'valor_anterior',
        'valor_novo',
        'criado_em',
    ]

    def has_add_permission(self, request):
        return False