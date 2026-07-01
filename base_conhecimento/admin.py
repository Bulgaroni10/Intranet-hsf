from django.contrib import admin

from .models import (
    CategoriaConhecimento,
    DocumentoConhecimento,
    LeituraDocumentoConhecimento,
)


@admin.register(CategoriaConhecimento)
class CategoriaConhecimentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'ativo',
        'ordem',
        'atualizado_em',
    )

    list_filter = (
        'ativo',
    )

    search_fields = (
        'nome',
        'descricao',
    )

    readonly_fields = (
        'criado_em',
        'atualizado_em',
    )

    fieldsets = (
        ('Categoria', {
            'fields': (
                'nome',
                'descricao',
                'ativo',
                'ordem',
            )
        }),
        ('Controle', {
            'fields': (
                'criado_em',
                'atualizado_em',
            )
        }),
    )

    ordering = (
        'ordem',
        'nome',
    )


@admin.register(DocumentoConhecimento)
class DocumentoConhecimentoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'tipo',
        'categoria',
        'unidade',
        'setor',
        'status',
        'leitura_obrigatoria',
        'ativo',
        'data_revisao',
        'atualizado_em',
    )

    list_filter = (
        'tipo',
        'categoria',
        'unidade',
        'setor',
        'status',
        'leitura_obrigatoria',
        'ativo',
        'data_revisao',
    )

    search_fields = (
        'titulo',
        'descricao',
        'versao',
        'link_externo',
        'categoria__nome',
        'unidade__nome',
        'unidade__sigla',
        'setor__nome',
    )

    filter_horizontal = (
        'grupos_permitidos',
    )

    readonly_fields = (
        'criado_em',
        'atualizado_em',
    )

    fieldsets = (
        ('Identificação', {
            'fields': (
                'titulo',
                'tipo',
                'categoria',
                'descricao',
            )
        }),
        ('Destino / Acesso', {
            'fields': (
                'unidade',
                'setor',
                'grupos_permitidos',
            )
        }),
        ('Arquivo / Link', {
            'fields': (
                'arquivo',
                'link_externo',
            )
        }),
        ('Revisão e versão', {
            'fields': (
                'versao',
                'status',
                'leitura_obrigatoria',
                'responsavel_revisao',
                'data_revisao',
            )
        }),
        ('Controle', {
            'fields': (
                'ativo',
                'ordem',
                'criado_por',
                'atualizado_por',
                'criado_em',
                'atualizado_em',
            )
        }),
    )

    ordering = (
        'categoria__nome',
        'setor__nome',
        'titulo',
    )

    def save_model(self, request, obj, form, change):
        if not obj.criado_por:
            obj.criado_por = request.user

        obj.atualizado_por = request.user

        super().save_model(request, obj, form, change)


@admin.register(LeituraDocumentoConhecimento)
class LeituraDocumentoConhecimentoAdmin(admin.ModelAdmin):
    list_display = (
        'documento',
        'usuario',
        'unidade_usuario',
        'setor_usuario',
        'versao_documento',
        'confirmado_em',
        'ip_origem',
    )

    list_filter = (
        'documento',
        'unidade_usuario',
        'setor_usuario',
        'versao_documento',
        'confirmado_em',
    )

    search_fields = (
        'documento__titulo',
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
        'usuario__email',
        'unidade_usuario__nome',
        'setor_usuario__nome',
        'versao_documento',
        'ip_origem',
    )

    readonly_fields = (
        'documento',
        'usuario',
        'unidade_usuario',
        'setor_usuario',
        'versao_documento',
        'confirmado_em',
        'ip_origem',
        'user_agent',
    )

    ordering = (
        '-confirmado_em',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False