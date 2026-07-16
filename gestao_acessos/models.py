from django.conf import settings
from django.db import models
from pathlib import Path
from uuid import uuid4

from usuarios.models import Setor, Unidade


class SolicitacaoAcesso(models.Model):
    TIPO_CHOICES = [
        ('admissao', 'Admissão / novos acessos'),
        ('alteracao', 'Alteração de acesso'),
        ('mudanca_setor', 'Mudança de setor'),
        ('bloqueio', 'Bloqueio temporário'),
        ('desligamento', 'Desligamento / revogação'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovada', 'Aprovada'),
        ('em_execucao', 'Em execução'),
        ('concluida', 'Concluída'),
        ('reprovada', 'Reprovada'),
        ('cancelada', 'Cancelada'),
    ]
    PRIORIDADE_CHOICES = [
        ('normal', 'Normal'), ('alta', 'Alta'), ('urgente', 'Urgente'),
    ]

    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='solicitacoes_acesso')
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name='solicitacoes_acesso')
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='solicitacoes_acesso_abertas',
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitacoes_acesso_responsavel',
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    colaborador_nome = models.CharField(max_length=180)
    colaborador_matricula = models.CharField(max_length=60, blank=True)
    colaborador_cargo = models.CharField(max_length=120, blank=True)
    sistemas = models.TextField(help_text='Informe um sistema ou acesso por linha.')
    justificativa = models.TextField()
    data_necessaria = models.DateField(null=True, blank=True)
    observacao_ti = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Solicitação de acesso'
        verbose_name_plural = 'Solicitações de acesso'

    def __str__(self):
        return f'#{self.pk} - {self.colaborador_nome}'


class HistoricoSolicitacaoAcesso(models.Model):
    solicitacao = models.ForeignKey(
        SolicitacaoAcesso, on_delete=models.CASCADE, related_name='historico',
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']


def caminho_anexo_acesso(instance, filename):
    extensao = Path(filename).suffix.lower()
    return f'gestao_acessos/{instance.solicitacao_id}/{uuid4().hex}{extensao}'


class AnexoSolicitacaoAcesso(models.Model):
    solicitacao = models.ForeignKey(
        SolicitacaoAcesso, on_delete=models.CASCADE, related_name='anexos',
    )
    arquivo = models.FileField(upload_to=caminho_anexo_acesso)
    nome_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=150, default='application/octet-stream')
    tamanho = models.PositiveBigIntegerField(default=0)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']

    def __str__(self):
        return self.nome_original
