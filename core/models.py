from django.conf import settings
from django.db import models


class NotificacaoUsuario(models.Model):
    TIPO_CHOICES = [
        ('info', 'Informação'),
        ('success', 'Sucesso'),
        ('warning', 'Alerta'),
        ('danger', 'Crítica'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes',
    )
    unidade = models.ForeignKey(
        'usuarios.Unidade', on_delete=models.CASCADE, null=True, blank=True,
        related_name='notificacoes_usuarios',
    )
    titulo = models.CharField(max_length=160)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='info')
    icone = models.CharField(max_length=30, default='🔔')
    link = models.CharField(max_length=500, blank=True)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    lida_em = models.DateTimeField(null=True, blank=True)
    origem = models.CharField(max_length=80)
    objeto_id = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'origem', 'objeto_id'],
                name='notificacao_unica_por_usuario_origem_objeto',
            ),
        ]

    def __str__(self):
        return f'{self.usuario}: {self.titulo}'


class FavoritoModulo(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favoritos_modulos',
    )
    modulo = models.ForeignKey(
        'modulos.Modulo',
        on_delete=models.CASCADE,
        related_name='favoritos_usuarios',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['modulo__ordem', 'modulo__nome']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'modulo'],
                name='favorito_modulo_unico_por_usuario',
            ),
        ]

    def __str__(self):
        return f'{self.usuario}: {self.modulo}'
