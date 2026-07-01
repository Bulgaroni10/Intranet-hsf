from django.contrib import admin

from .models import ConversaChat, MensagemChat


@admin.register(ConversaChat)
class ConversaChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'nome_grupo', 'criado_por', 'ativo', 'criado_em', 'atualizado_em')
    list_filter = ('tipo', 'ativo', 'criado_em')
    search_fields = ('nome_grupo', 'participantes__username', 'participantes__first_name', 'participantes__last_name')
    filter_horizontal = ('participantes',)
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(MensagemChat)
class MensagemChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversa', 'remetente', 'criado_em')
    list_filter = ('criado_em',)
    search_fields = ('texto', 'remetente__username', 'remetente__first_name', 'remetente__last_name')
    filter_horizontal = ('lida_por',)
    readonly_fields = ('criado_em',)
