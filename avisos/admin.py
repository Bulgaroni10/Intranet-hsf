from django.contrib import admin

from .models import AvisoComunicado


@admin.register(AvisoComunicado)
class AvisoComunicadoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'tipo',
        'prioridade',
        'unidade',
        'fixar_no_topo',
        'exibir_no_dashboard',
        'ativo',
        'publicado_em',
        'expira_em',
    )

    list_filter = (
        'tipo',
        'prioridade',
        'unidade',
        'fixar_no_topo',
        'exibir_no_dashboard',
        'ativo',
        'publicado_em',
    )

    search_fields = (
        'titulo',
        'resumo',
        'mensagem',
        'unidade__nome',
        'unidade__sigla',
    )

    autocomplete_fields = (
        'unidade',
        'grupos_permitidos',
        'criado_por',
    )

    filter_horizontal = (
        'grupos_permitidos',
    )

    ordering = (
        '-fixar_no_topo',
        '-publicado_em',
        'titulo',
    )

    fieldsets = (
        ('Identificação', {
            'fields': (
                'titulo',
                'tipo',
                'prioridade',
                'resumo',
                'mensagem',
            )
        }),
        ('Visibilidade', {
            'fields': (
                'unidade',
                'grupos_permitidos',
                'fixar_no_topo',
                'exibir_no_dashboard',
                'ativo',
            )
        }),
        ('Datas', {
            'fields': (
                'publicado_em',
                'expira_em',
            )
        }),
        ('Anexos e links', {
            'fields': (
                'link_externo',
                'arquivo',
            )
        }),
        ('Controle interno', {
            'fields': (
                'criado_por',
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.criado_por:
            obj.criado_por = request.user

        super().save_model(request, obj, form, change)