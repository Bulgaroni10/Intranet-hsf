from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        'criado_em',
        'modulo',
        'acao',
        'titulo',
        'usuario',
        'unidade',
        'modelo',
        'objeto_id',
        'ip_origem',
    )

    list_filter = (
        'modulo',
        'acao',
        'usuario',
        'unidade',
        'criado_em',
    )

    search_fields = (
        'titulo',
        'descricao',
        'modelo',
        'objeto_id',
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
        'usuario__email',
        'unidade__nome',
        'unidade__sigla',
        'ip_origem',
    )

    readonly_fields = (
        'modulo',
        'acao',
        'titulo',
        'descricao',
        'modelo',
        'objeto_id',
        'usuario',
        'unidade',
        'ip_origem',
        'criado_em',
    )

    ordering = (
        '-criado_em',
    )

    date_hierarchy = 'criado_em'