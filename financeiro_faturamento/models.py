from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models

from usuarios.models import Unidade


class RegistroFinanceiro(models.Model):
    AREA_CHOICES = [('financeiro', 'Financeiro'), ('faturamento', 'Faturamento')]
    TIPO_CHOICES = [
        ('contas_pagar', 'Contas a pagar'), ('contas_receber', 'Contas a receber'),
        ('fechamento', 'Fechamento de competência'), ('recurso_glosa', 'Recurso de glosa'),
        ('envio_conta', 'Envio de conta'), ('conciliacao', 'Conciliação'),
        ('documentacao', 'Documentação'), ('outro', 'Outro'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'), ('em_andamento', 'Em andamento'),
        ('aguardando', 'Aguardando retorno'), ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    PRIORIDADE_CHOICES = [('normal', 'Normal'), ('alta', 'Alta'), ('critica', 'Crítica')]

    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='registros_financeiros')
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='registros_financeiros_criados')
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registros_financeiros_responsavel',
    )
    area = models.CharField(max_length=20, choices=AREA_CHOICES)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=180)
    competencia = models.DateField(help_text='Utilize o primeiro dia do mês de referência.')
    prazo = models.DateField(null=True, blank=True)
    entidade = models.CharField(max_length=180, blank=True, help_text='Convênio, fornecedor ou cliente relacionado.')
    valor = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    prioridade = models.CharField(max_length=15, choices=PRIORIDADE_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    descricao = models.TextField()
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-competencia', 'prazo', '-criado_em']
        verbose_name = 'Registro financeiro/faturamento'
        verbose_name_plural = 'Registros financeiros/faturamento'


class HistoricoFinanceiro(models.Model):
    registro = models.ForeignKey(RegistroFinanceiro, on_delete=models.CASCADE, related_name='historico')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']


def caminho_anexo(instance, filename):
    return f'financeiro_faturamento/{instance.registro_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class AnexoFinanceiro(models.Model):
    registro = models.ForeignKey(RegistroFinanceiro, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to=caminho_anexo)
    nome_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=150, default='application/octet-stream')
    tamanho = models.PositiveBigIntegerField(default=0)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']
