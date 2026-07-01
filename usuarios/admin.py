from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario, Unidade, Setor


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla', 'ativo')
    search_fields = ('nome', 'sigla')
    list_filter = ('ativo',)


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')
    search_fields = ('nome',)
    list_filter = ('ativo',)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario

    list_display = (
        'username',
        'first_name',
        'last_name',
        'email',
        'unidade',
        'setor',
        'tipo_prestador',
        'tipo_conselho',
        'numero_conselho',
        'uf_conselho',
        'is_active',
        'primeiro_acesso',
    )

    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'groups',
        'unidade',
        'setor',
        'tipo_prestador',
        'tipo_conselho',
        'primeiro_acesso',
    )

    search_fields = (
        'username',
        'first_name',
        'last_name',
        'email',
        'numero_conselho',
    )

    fieldsets = UserAdmin.fieldsets + (
        ('Dados da Intranet', {
            'fields': (
                'unidade',
                'setor',
                'tipo_prestador',
                'tipo_conselho',
                'numero_conselho',
                'uf_conselho',
                'telefone',
                'primeiro_acesso',
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Dados da Intranet', {
            'fields': (
                'unidade',
                'setor',
                'tipo_prestador',
                'tipo_conselho',
                'numero_conselho',
                'uf_conselho',
                'telefone',
                'primeiro_acesso',
            )
        }),
    )