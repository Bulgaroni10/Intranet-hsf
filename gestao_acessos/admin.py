from django.contrib import admin

from .models import AnexoSolicitacaoAcesso, HistoricoSolicitacaoAcesso, SolicitacaoAcesso


class HistoricoInline(admin.TabularInline):
    model = HistoricoSolicitacaoAcesso
    extra = 0
    readonly_fields = ('usuario', 'status_anterior', 'status_novo', 'observacao', 'criado_em')


class AnexoInline(admin.TabularInline):
    model = AnexoSolicitacaoAcesso
    extra = 0


@admin.register(SolicitacaoAcesso)
class SolicitacaoAcessoAdmin(admin.ModelAdmin):
    list_display = ('id', 'colaborador_nome', 'unidade', 'tipo', 'status', 'criado_em')
    list_filter = ('unidade', 'tipo', 'status')
    search_fields = ('colaborador_nome', 'cpf', 'numero_conselho', 'especialidade', 'sistemas')
    inlines = [HistoricoInline, AnexoInline]
