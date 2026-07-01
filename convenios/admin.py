from django.contrib import admin

from .models import (
    Convenio,
    PlanoConvenio,
    Especialidade,
    RegraAtendimentoConvenio,
    ProcedimentoProibidoPlano,
    ImportacaoMV,
    ItemImportacaoMV,
)


class PlanoConvenioInline(admin.TabularInline):
    model = PlanoConvenio
    extra = 0
    fields = (
        'codigo_mv',
        'nome',
        'regra_codigo_mv',
        'regra_nome_mv',
        'indice_codigo_mv',
        'indice_nome_mv',
        'ativo',
    )


class ItemImportacaoMVInline(admin.TabularInline):
    model = ItemImportacaoMV
    extra = 0
    can_delete = False
    readonly_fields = (
        'linha',
        'status',
        'mensagem',
        'dados',
        'criado_em',
    )

    fields = (
        'linha',
        'status',
        'mensagem',
        'dados',
        'criado_em',
    )

    ordering = (
        'linha',
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_mv',
        'nome',
        'tipo_mv',
        'ativo',
    )

    list_filter = (
        'tipo_mv',
        'ativo',
    )

    search_fields = (
        'codigo_mv',
        'nome',
        'tipo_mv',
    )

    inlines = [
        PlanoConvenioInline,
    ]

    ordering = (
        'nome',
    )


@admin.register(PlanoConvenio)
class PlanoConvenioAdmin(admin.ModelAdmin):
    list_display = (
        'convenio',
        'codigo_mv',
        'nome',
        'regra_codigo_mv',
        'regra_nome_mv',
        'indice_codigo_mv',
        'indice_nome_mv',
        'ativo',
    )

    list_filter = (
        'convenio',
        'ativo',
    )

    search_fields = (
        'convenio__nome',
        'convenio__codigo_mv',
        'codigo_mv',
        'nome',
        'regra_codigo_mv',
        'regra_nome_mv',
        'indice_codigo_mv',
        'indice_nome_mv',
    )

    autocomplete_fields = (
        'convenio',
    )

    ordering = (
        'convenio__nome',
        'nome',
        'codigo_mv',
    )


@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'ativo',
    )

    list_filter = (
        'ativo',
    )

    search_fields = (
        'nome',
    )

    ordering = (
        'nome',
    )


@admin.register(RegraAtendimentoConvenio)
class RegraAtendimentoConvenioAdmin(admin.ModelAdmin):
    list_display = (
        'unidade',
        'convenio',
        'plano',
        'tipo_atendimento',
        'especialidade',
        'status',
        'exige_autorizacao',
        'ativo',
        'atualizado_em',
    )

    list_filter = (
        'unidade',
        'convenio',
        'plano',
        'tipo_atendimento',
        'especialidade',
        'status',
        'exige_autorizacao',
        'ativo',
    )

    search_fields = (
        'unidade__nome',
        'unidade__sigla',
        'convenio__nome',
        'convenio__codigo_mv',
        'plano__nome',
        'plano__codigo_mv',
        'especialidade__nome',
        'observacao',
    )

    autocomplete_fields = (
        'unidade',
        'convenio',
        'plano',
        'especialidade',
    )

    readonly_fields = (
        'atualizado_em',
    )

    fieldsets = (
        ('Identificação da regra', {
            'fields': (
                'unidade',
                'convenio',
                'plano',
                'tipo_atendimento',
                'especialidade',
            )
        }),
        ('Status operacional', {
            'fields': (
                'status',
                'exige_autorizacao',
                'observacao',
                'ativo',
            )
        }),
        ('Controle', {
            'fields': (
                'atualizado_em',
            )
        }),
    )

    ordering = (
        'unidade',
        'convenio',
        'plano',
        'tipo_atendimento',
        'especialidade',
    )


@admin.register(ProcedimentoProibidoPlano)
class ProcedimentoProibidoPlanoAdmin(admin.ModelAdmin):
    list_display = (
        'convenio',
        'plano',
        'codigo_procedimento',
        'descricao_procedimento',
        'ativo',
        'atualizado_em',
    )

    list_filter = (
        'convenio',
        'plano',
        'ativo',
    )

    search_fields = (
        'convenio__nome',
        'convenio__codigo_mv',
        'plano__nome',
        'plano__codigo_mv',
        'codigo_procedimento',
        'descricao_procedimento',
    )

    autocomplete_fields = (
        'convenio',
        'plano',
    )

    readonly_fields = (
        'criado_em',
        'atualizado_em',
    )

    fieldsets = (
        ('Convênio e plano', {
            'fields': (
                'convenio',
                'plano',
            )
        }),
        ('Procedimento', {
            'fields': (
                'codigo_procedimento',
                'descricao_procedimento',
            )
        }),
        ('Controle', {
            'fields': (
                'ativo',
                'criado_em',
                'atualizado_em',
            )
        }),
    )

    ordering = (
        'convenio',
        'plano',
        'descricao_procedimento',
    )


@admin.register(ImportacaoMV)
class ImportacaoMVAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tipo',
        'status',
        'usuario',
        'total_linhas',
        'total_sucesso',
        'total_erros',
        'criado_em',
        'finalizado_em',
    )

    list_filter = (
        'tipo',
        'status',
        'criado_em',
    )

    search_fields = (
        'id',
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
        'mensagem',
    )

    readonly_fields = (
        'status',
        'usuario',
        'total_linhas',
        'total_sucesso',
        'total_erros',
        'mensagem',
        'criado_em',
        'iniciado_em',
        'finalizado_em',
    )

    fieldsets = (
        ('Arquivo', {
            'fields': (
                'tipo',
                'arquivo',
            )
        }),
        ('Resultado', {
            'fields': (
                'status',
                'usuario',
                'total_linhas',
                'total_sucesso',
                'total_erros',
                'mensagem',
            )
        }),
        ('Datas', {
            'fields': (
                'criado_em',
                'iniciado_em',
                'finalizado_em',
            )
        }),
    )

    inlines = [
        ItemImportacaoMVInline,
    ]

    ordering = (
        '-criado_em',
    )


@admin.register(ItemImportacaoMV)
class ItemImportacaoMVAdmin(admin.ModelAdmin):
    list_display = (
        'importacao',
        'linha',
        'status',
        'mensagem',
        'criado_em',
    )

    list_filter = (
        'status',
        'importacao__tipo',
        'criado_em',
    )

    search_fields = (
        'mensagem',
        'dados',
    )

    readonly_fields = (
        'importacao',
        'linha',
        'status',
        'mensagem',
        'dados',
        'criado_em',
    )

    ordering = (
        '-criado_em',
        'linha',
    )