from django.contrib import admin

from .models import RamalContato


@admin.register(RamalContato)
class RamalContatoAdmin(admin.ModelAdmin):
    list_display = (
        'unidade',
        'tipo',
        'setor',
        'nome',
        'cargo_funcao',
        'ramal',
        'telefone',
        'celular',
        'whatsapp',
        'email',
        'ativo',
        'ordem',
    )

    list_filter = (
        'unidade',
        'tipo',
        'setor',
        'ativo',
    )

    search_fields = (
        'unidade__nome',
        'unidade__sigla',
        'setor',
        'nome',
        'cargo_funcao',
        'ramal',
        'telefone',
        'celular',
        'whatsapp',
        'email',
        'localizacao',
        'observacao',
    )

    autocomplete_fields = (
        'unidade',
    )

    readonly_fields = (
        'criado_em',
        'atualizado_em',
    )

    fieldsets = (
        ('Identificação', {
            'fields': (
                'unidade',
                'tipo',
                'setor',
                'nome',
                'cargo_funcao',
            )
        }),
        ('Contato', {
            'fields': (
                'ramal',
                'telefone',
                'celular',
                'whatsapp',
                'email',
            )
        }),
        ('Localização e observações', {
            'fields': (
                'localizacao',
                'observacao',
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
        'unidade',
        'setor',
        'ordem',
        'nome',
    )