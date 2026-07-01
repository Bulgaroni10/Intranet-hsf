from django.contrib.auth.models import Group
from django.db import models

from modulos.models import Modulo
from usuarios.models import Unidade


class ConteudoModulo(models.Model):
    TIPO_CHOICES = [
        ('manual', 'Manual'),
        ('convenio', 'Convênio'),
        ('contingencia', 'Contingência'),
        ('link', 'Link útil'),
        ('chamado', 'Chamado externo'),
        ('observacao', 'Observação'),
    ]

    modulo = models.ForeignKey(
        Modulo,
        on_delete=models.CASCADE,
        related_name='conteudos'
    )

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conteudos',
        help_text='Deixe em branco para aparecer para todas as unidades.'
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES
    )

    titulo = models.CharField(max_length=180)

    descricao = models.TextField(blank=True)

    arquivo = models.FileField(
        upload_to='conteudos/%Y/%m/',
        blank=True,
        null=True,
        help_text='Use para PDF, DOCX, XLSX ou arquivos internos.'
    )

    link_externo = models.URLField(
        blank=True,
        help_text='Use para links externos ou sistemas internos.'
    )

    grupos_permitidos = models.ManyToManyField(
        Group,
        blank=True,
        related_name='conteudos_permitidos',
        help_text='Se não selecionar nenhum grupo, aparece para todos os usuários com acesso ao módulo.'
    )

    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conteúdo do módulo'
        verbose_name_plural = 'Conteúdos dos módulos'
        ordering = ['tipo', 'ordem', 'titulo']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.titulo}'