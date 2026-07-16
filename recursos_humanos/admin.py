from django.contrib import admin

from .models import AnexoRH, HistoricoRH, SolicitacaoRH


class AnexoInline(admin.TabularInline):
    model = AnexoRH
    extra = 0


@admin.register(SolicitacaoRH)
class SolicitacaoRHAdmin(admin.ModelAdmin):
    list_display = ('id', 'assunto', 'solicitante', 'unidade', 'tipo', 'status', 'criado_em')
    list_filter = ('unidade', 'tipo', 'status')
    search_fields = ('assunto', 'descricao', 'solicitante__username')
    inlines = (AnexoInline,)


admin.site.register(HistoricoRH)
