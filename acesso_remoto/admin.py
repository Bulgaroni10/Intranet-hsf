from django.contrib import admin

from .models import AnexoAcessoRemoto, HistoricoAcessoRemoto, SolicitacaoAcessoRemoto


class AnexoInline(admin.TabularInline):
    model = AnexoAcessoRemoto
    extra = 0
    readonly_fields = ('nome_original', 'tamanho', 'enviado_por', 'criado_em')


@admin.register(SolicitacaoAcessoRemoto)
class SolicitacaoAcessoRemotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'unidade', 'tipo_acesso', 'status', 'inicio_validade', 'fim_validade')
    list_filter = ('unidade', 'status', 'tipo_acesso', 'vinculo')
    search_fields = ('nome', 'cpf', 'email', 'sistema_destino')
    inlines = (AnexoInline,)


admin.site.register(HistoricoAcessoRemoto)
