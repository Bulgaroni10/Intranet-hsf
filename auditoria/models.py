from django.contrib.auth import get_user_model
from django.db import models

from usuarios.models import Unidade


class RegistroAuditoria(models.Model):
    ACAO_CHOICES = [
        ('criado', 'Criado'),
        ('alterado', 'Alterado'),
        ('excluido', 'Excluído'),
        ('encerrado', 'Encerrado'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('outro', 'Outro'),
    ]

    MODULO_CHOICES = [
        ('avisos', 'Avisos / Comunicados'),
        ('documentos', 'Documentos / Protocolos ONA'),
        ('status_sistemas', 'Status dos Sistemas'),
        ('conteudos', 'Conteúdos / Manuais / Links'),
        ('ramais', 'Ramais e Contatos'),
        ('convenios', 'Convênios MV'),
        ('usuarios', 'Usuários'),
        ('sistema', 'Sistema'),
        ('outro', 'Outro'),
    ]

    modulo = models.CharField(
        max_length=50,
        choices=MODULO_CHOICES,
        default='outro'
    )

    acao = models.CharField(
        max_length=30,
        choices=ACAO_CHOICES,
        default='outro'
    )

    titulo = models.CharField(max_length=220)

    descricao = models.TextField(blank=True)

    modelo = models.CharField(
        max_length=120,
        blank=True,
        help_text='Nome técnico do model. Ex: AvisoComunicado.'
    )

    objeto_id = models.CharField(
        max_length=80,
        blank=True,
        help_text='ID do registro relacionado.'
    )

    usuario = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_auditoria'
    )

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_auditoria'
    )

    ip_origem = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de auditoria'
        verbose_name_plural = 'Registros de auditoria'
        ordering = ['-criado_em']

    def __str__(self):
        usuario = self.usuario.username if self.usuario else 'Sistema'
        return f'{self.get_acao_display()} - {self.titulo} - {usuario}'