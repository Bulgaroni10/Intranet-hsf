from django.contrib.auth.models import Group
from django.db import models


class Modulo(models.Model):
    CATEGORIA_CHOICES = [
        ('assistencial', 'Sistemas assistenciais'),
        ('administrativo', 'Administrativo e documentos'),
        ('tecnologia', 'Tecnologia e acessos'),
        ('gestao', 'Gestão'),
    ]

    nome = models.CharField(max_length=120)
    descricao = models.CharField(max_length=180, blank=True)
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES)
    icone = models.CharField(max_length=10, default='📁')
    tag = models.CharField(max_length=30, blank=True)
    link = models.CharField(max_length=255, default='#')
    palavras_chave = models.TextField(blank=True)

    grupos_permitidos = models.ManyToManyField(
        Group,
        blank=True,
        related_name='modulos_permitidos',
        help_text='Se não selecionar nenhum grupo, o módulo aparece para todos os usuários logados.'
    )

    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'
        ordering = ['categoria', 'ordem', 'nome']

    def __str__(self):
        return self.nome