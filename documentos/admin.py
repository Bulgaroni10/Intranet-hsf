from django.contrib import admin

from .models import DocumentoProtocolo


@admin.register(DocumentoProtocolo)
class DocumentoProtocoloAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'titulo',
        'tipo',
        'categoria',
        'unidade',
        'setor',
        'versao',
        'status',
        'leitura_obrigatoria',
        'data_publicacao',
        'data_validade',
        'ativo',
    )

    list_filter = (
        'tipo',
        'categoria',
        'status',
        'unidade',
        'setor',
        'grupos_permitidos',
        'unidades_compartilhadas',
        'leitura_obrigatoria',
        'exibir_no_dashboard',
        'ativo',
        'data_publicacao',
        'data_validade',
    )

    search_fields = (
        'codigo',
        'titulo',
        'descricao',
        'responsavel',
        'unidade__nome',
        'unidade__sigla',
        'unidades_compartilhadas__nome',
        'unidades_compartilhadas__sigla',
        'setor__nome',
        'grupos_permitidos__name',
    )

    autocomplete_fields = (
        'unidade',
        'setor',
        'grupos_permitidos',
        'criado_por',
    )

    filter_horizontal = (
        'unidades_compartilhadas',
        'grupos_permitidos',
    )

    ordering = (
        'categoria',
        'tipo',
        'titulo',
    )

    readonly_fields = (
        'criado_em',
        'atualizado_em',
    )

    fieldsets = (
        ('Identificação', {
            'fields': (
                'codigo',
                'titulo',
                'tipo',
                'categoria',
                'descricao',
            )
        }),
        ('Vínculo interno e permissões', {
            'fields': (
                'unidade',
                'unidades_compartilhadas',
                'setor',
                'grupos_permitidos',
            ),
            'description': (
                'Deixe a unidade em branco para documento geral. '
                'Use unidades compartilhadas quando o documento for da unidade principal, '
                'mas também precisar aparecer para outras unidades específicas.'
            )
        }),
        ('Documento', {
            'fields': (
                'arquivo',
                'versao',
                'responsavel',
            )
        }),
        ('Datas, status e dashboard', {
            'fields': (
                'data_publicacao',
                'data_validade',
                'status',
                'exibir_no_dashboard',
                'leitura_obrigatoria',
                'ativo',
            )
        }),
        ('Controle interno', {
            'fields': (
                'criado_por',
                'criado_em',
                'atualizado_em',
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.criado_por:
            obj.criado_por = request.user

        super().save_model(request, obj, form, change)