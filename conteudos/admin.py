from django.contrib import admin

from .models import ConteudoModulo


@admin.register(ConteudoModulo)
class ConteudoModuloAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'modulo',
        'tipo',
        'unidade',
        'ativo',
        'ordem',
        'atualizado_em',
    )

    list_filter = (
        'modulo',
        'tipo',
        'unidade',
        'ativo',
        'grupos_permitidos',
    )

    search_fields = (
        'titulo',
        'descricao',
        'link_externo',
        'arquivo',
        'unidade__nome',
        'unidade__sigla',
        'modulo__nome',
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
                'modulo',
                'unidade',
                'tipo',
                'titulo',
                'descricao',
            )
        }),
        ('Arquivo / Link', {
            'fields': (
                'arquivo',
                'link_externo',
            )
        }),
        ('Permissões', {
            'fields': (
                'grupos_permitidos',
            )
        }),
        ('Controle', {
            'fields': (
                'ativo',
                'ordem',
                'criado_em',
                'atualizado_em',
            )
        }),
    )

    ordering = (
        'modulo',
        'tipo',
        'ordem',
        'titulo',
    )