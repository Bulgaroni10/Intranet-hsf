from django.contrib import admin

from .models import Modulo


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'categoria',
        'tag',
        'link',
        'ativo',
        'ordem',
    )

    list_filter = (
        'categoria',
        'ativo',
        'grupos_permitidos',
    )

    search_fields = (
        'nome',
        'descricao',
        'palavras_chave',
        'tag',
    )

    filter_horizontal = (
        'grupos_permitidos',
    )

    ordering = (
        'categoria',
        'ordem',
        'nome',
    )