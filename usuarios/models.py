import re

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Unidade(models.Model):
    nome = models.CharField(max_length=150)
    sigla = models.CharField(max_length=20, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Unidade'
        verbose_name_plural = 'Unidades'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Setor(models.Model):
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Setor'
        verbose_name_plural = 'Setores'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Usuario(AbstractUser):
    TIPO_PRESTADOR_CHOICES = [
        ('colaborador', 'Colaborador'),
        ('medico', 'Médico'),
        ('enfermeiro', 'Enfermeiro / Técnico de Enfermagem'),
        ('fisioterapeuta', 'Fisioterapeuta'),
        ('terceiro', 'Terceiro'),
        ('rt', 'Responsável Técnico'),
        ('gerencia', 'Gerência'),
        ('diretoria', 'Diretoria'),
        ('ti', 'Tecnologia da Informação'),
    ]

    TIPO_CONSELHO_CHOICES = [
        ('', 'Não se aplica'),
        ('CRM', 'CRM'),
        ('COREN', 'COREN'),
        ('CREFITO', 'CREFITO'),
        ('OUTRO', 'Outro'),
    ]

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )

    setor = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )

    tipo_prestador = models.CharField(
        max_length=30,
        choices=TIPO_PRESTADOR_CHOICES,
        default='colaborador'
    )

    tipo_conselho = models.CharField(
        max_length=20,
        choices=TIPO_CONSELHO_CHOICES,
        blank=True,
        default=''
    )

    numero_conselho = models.CharField(
        max_length=30,
        blank=True,
        help_text='CRM, COREN ou CREFITO quando aplicável.'
    )

    uf_conselho = models.CharField(
        max_length=2,
        blank=True,
        help_text='UF do conselho. Exemplo: SP.'
    )

    telefone = models.CharField(max_length=30, blank=True)

    primeiro_acesso = models.BooleanField(
        default=True,
        help_text='Se marcado, o usuário deverá trocar a senha no primeiro acesso.'
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def clean(self):
        super().clean()

        if self.username:
            self.username = self.username.strip().lower()

        if self.uf_conselho:
            self.uf_conselho = self.uf_conselho.strip().upper()

        profissionais_com_conselho = {
            'medico': 'CRM',
            'enfermeiro': 'COREN',
            'fisioterapeuta': 'CREFITO',
        }

        if self.tipo_prestador in profissionais_com_conselho:
            conselho_esperado = profissionais_com_conselho[self.tipo_prestador]

            if not self.numero_conselho:
                raise ValidationError({
                    'numero_conselho': f'Informe o número do {conselho_esperado}.'
                })

            if not self.tipo_conselho:
                raise ValidationError({
                    'tipo_conselho': f'Informe o tipo de conselho: {conselho_esperado}.'
                })

            if self.tipo_conselho != conselho_esperado:
                raise ValidationError({
                    'tipo_conselho': f'Para este tipo de prestador, o conselho deve ser {conselho_esperado}.'
                })

            if not self.uf_conselho:
                raise ValidationError({
                    'uf_conselho': 'Informe a UF do conselho. Exemplo: SP.'
                })

            if not re.match(r'^[a-z]+[0-9]+$', self.username or ''):
                raise ValidationError({
                    'username': 'Para médico, enfermagem ou fisioterapia, use o padrão nome+número do conselho. Exemplo: kauan145236.'
                })

        else:
            if not re.match(r'^[a-z]+(\.[a-z]+)+$', self.username or ''):
                raise ValidationError({
                    'username': 'Para usuários comuns, use o padrão nome.sobrenome. Exemplo: kauan.silva.'
                })

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.strip().lower()

        if self.uf_conselho:
            self.uf_conselho = self.uf_conselho.strip().upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username