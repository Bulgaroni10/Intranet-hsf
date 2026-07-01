from django.conf import settings
from django.db import models
from django.utils import timezone


class ConversaChat(models.Model):
    participantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversas_chat'
    )

    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Conversa'
        verbose_name_plural = 'Conversas'
        ordering = ['-atualizado_em']

    def __str__(self):
        nomes = []

        for usuario in self.participantes.all()[:3]:
            nome = usuario.get_full_name() or usuario.username
            nomes.append(nome)

        if nomes:
            return ' / '.join(nomes)

        return f'Conversa #{self.id}'


class MensagemChat(models.Model):
    conversa = models.ForeignKey(
        ConversaChat,
        on_delete=models.CASCADE,
        related_name='mensagens'
    )

    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensagens_chat_enviadas'
    )

    texto = models.TextField()

    lida_por = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='mensagens_chat_lidas'
    )

    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ['criado_em']

    def __str__(self):
        return f'{self.remetente} - {self.criado_em:%d/%m/%Y %H:%M}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        ConversaChat.objects.filter(id=self.conversa_id).update(
            atualizado_em=timezone.now()
        )