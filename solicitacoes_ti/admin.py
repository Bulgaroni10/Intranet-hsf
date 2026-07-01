from django.contrib import admin

from .models import SolicitacaoTI, MensagemSolicitacaoTI


class MensagemSolicitacaoTIInline(admin.TabularInline):
    model = MensagemSolicitacaoTI
    extra = 0
    readonly_fields = (
        'criado_em',
    )

    fields = (
        'origem',
        'autor',
        'mensagem',
        'criado_em',
        'lida_pela_ti',
        'lida_pelo_solicitante',
    )


@admin.register(SolicitacaoTI)
class SolicitacaoTIAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'titulo',
        'tipo',
        'prioridade',
        'status',
        'unidade',
        'setor',
        'solicitante',
        'responsavel_ti',
        'visto_pela_ti',
        'conversa_iniciada',
        'criado_em',
        'resolvido_em',
        'ativo',
    )

    list_filter = (
        'tipo',
        'prioridade',
        'status',
        'unidade',
        'setor',
        'visto_pela_ti',
        'conversa_iniciada',
        'ativo',
        'criado_em',
    )

    search_fields = (
        'id',
        'titulo',
        'descricao',
        'equipamento',
        'resposta_ti',
        'solicitante__username',
        'solicitante__first_name',
        'solicitante__last_name',
        'responsavel_ti__username',
        'responsavel_ti__first_name',
        'responsavel_ti__last_name',
    )

    autocomplete_fields = (
        'unidade',
        'setor',
        'solicitante',
        'responsavel_ti',
    )

    readonly_fields = (
        'criado_em',
        'atualizado_em',
        'visto_pela_ti_em',
        'conversa_iniciada_em',
        'resolvido_em',
    )

    inlines = [
        MensagemSolicitacaoTIInline,
    ]

    ordering = (
        '-criado_em',
    )


@admin.register(MensagemSolicitacaoTI)
class MensagemSolicitacaoTIAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'solicitacao',
        'origem',
        'autor',
        'criado_em',
        'lida_pela_ti',
        'lida_pelo_solicitante',
    )

    list_filter = (
        'origem',
        'lida_pela_ti',
        'lida_pelo_solicitante',
        'criado_em',
    )

    search_fields = (
        'solicitacao__id',
        'solicitacao__titulo',
        'autor__username',
        'autor__first_name',
        'autor__last_name',
        'mensagem',
    )

    autocomplete_fields = (
        'solicitacao',
        'autor',
    )

    readonly_fields = (
        'criado_em',
    )

    ordering = (
        '-criado_em',
    )