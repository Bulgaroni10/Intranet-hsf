from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models

from usuarios.models import Setor, Unidade


class SolicitacaoRH(models.Model):
    TIPO_CHOICES = [
        ('beneficios', 'Benefícios'), ('ferias', 'Férias'),
        ('declaracao', 'Declaração / documento'), ('folha_ponto', 'Folha ou ponto'),
        ('cadastro', 'Atualização cadastral'), ('afastamento', 'Afastamento'),
        ('outro', 'Outro assunto'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'), ('em_analise', 'Em análise'),
        ('aguardando', 'Aguardando solicitante'), ('concluida', 'Concluída'),
        ('indeferida', 'Indeferida'), ('cancelada', 'Cancelada'),
    ]
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='solicitacoes_rh')
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name='solicitacoes_rh')
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='solicitacoes_rh')
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='atendimentos_rh',
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    assunto = models.CharField(max_length=180)
    descricao = models.TextField()
    telefone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    resposta_rh = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Solicitação de RH'
        verbose_name_plural = 'Solicitações de RH'

    def __str__(self):
        return f'#{self.pk} - {self.assunto}'


class HistoricoRH(models.Model):
    solicitacao = models.ForeignKey(SolicitacaoRH, on_delete=models.CASCADE, related_name='historico')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']


def caminho_anexo(instance, filename):
    return f'recursos_humanos/{instance.solicitacao_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class AnexoRH(models.Model):
    solicitacao = models.ForeignKey(SolicitacaoRH, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to=caminho_anexo)
    nome_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=150, default='application/octet-stream')
    tamanho = models.PositiveBigIntegerField(default=0)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']
