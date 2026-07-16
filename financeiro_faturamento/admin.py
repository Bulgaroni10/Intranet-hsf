from django.contrib import admin
from .models import AnexoFinanceiro, HistoricoFinanceiro, RegistroFinanceiro

class AnexoInline(admin.TabularInline): model = AnexoFinanceiro; extra = 0
@admin.register(RegistroFinanceiro)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'unidade', 'area', 'competencia', 'prazo', 'status')
    list_filter = ('unidade', 'area', 'tipo', 'status'); search_fields = ('titulo', 'entidade'); inlines = (AnexoInline,)
admin.site.register(HistoricoFinanceiro)
