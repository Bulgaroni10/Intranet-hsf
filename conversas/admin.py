from django.contrib import admin

from .models import ConversaChat, MensagemChat


@admin.register(ConversaChat)
class ConversaChatAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'criado_em',
        'atualizado_em',
        'ativo',
    ]

    list_filter = [
        'ativo',
        'criado_em',
        'atualizado_em',
    ]

    filter_horizontal = [
        'participantes',
    ]

    search_fields = [
        'participantes__username',
        'participantes__first_name',
        'participantes__last_name',
        'participantes__email',
    ]


@admin.register(MensagemChat)
class MensagemChatAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'conversa',
        'remetente',
        'criado_em',
    ]

    list_filter = [
        'criado_em',
    ]

    search_fields = [
        'texto',
        'remetente__username',
        'remetente__first_name',
        'remetente__last_name',
        'remetente__email',
    ]

    filter_horizontal = [
        'lida_por',
    ]