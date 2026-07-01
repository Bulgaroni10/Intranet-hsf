from django.contrib import admin

from .models import SistemaMonitorado, OcorrenciaSistema


@admin.register(SistemaMonitorado)
class SistemaMonitoradoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'categoria',
        'icone',
        'ativo',
        'ordem',
        'atualizado_em',
    )

    list_filter = (
        'categoria',
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
        ('Identificação', {
            'fields': (
                'nome',
                'descricao',
                'categoria',
                'icone',
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
        'ordem',
        'nome',
    )


@admin.register(OcorrenciaSistema)
class OcorrenciaSistemaAdmin(admin.ModelAdmin):
    list_display = (
        'sistema',
        'unidade',
        'status',
        'impacto',
        'titulo',
        'ativo',
        'aberto_em',
        'encerrado_em',
        'atualizado_em',
    )

    list_filter = (
        'sistema',
        'unidade',
        'status',
        'impacto',
        'ativo',
    )

    search_fields = (
        'sistema__nome',
        'unidade__nome',
        'unidade__sigla',
        'titulo',
        'mensagem',
        'previsao',
        'acao_ti',
        'causa_raiz',
        'solucao_aplicada',
        'observacao_encerramento',
    )

    autocomplete_fields = (
        'sistema',
        'unidade',
    )

    readonly_fields = (
        'aberto_em',
        'atualizado_em',
        'encerrado_em',
    )

    fieldsets = (
        ('Identificação', {
            'fields': (
                'sistema',
                'unidade',
                'status',
                'impacto',
                'titulo',
            )
        }),
        ('Comunicação aos usuários', {
            'fields': (
                'mensagem',
                'previsao',
            )
        }),
        ('Atuação da TI', {
            'fields': (
                'acao_ti',
                'causa_raiz',
                'solucao_aplicada',
                'observacao_encerramento',
            )
        }),
        ('Controle', {
            'fields': (
                'ativo',
                'aberto_em',
                'encerrado_em',
                'atualizado_em',
            )
        }),
    )

    ordering = (
        '-ativo',
        '-atualizado_em',
    )