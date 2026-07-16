from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models

from usuarios.models import Setor, Unidade


class SolicitacaoAcessoRemoto(models.Model):
    VINCULO_CHOICES = [
        ('colaborador', 'Colaborador'), ('medico', 'Médico / corpo clínico'),
        ('terceiro', 'Terceiro / fornecedor'),
    ]
    TIPO_CHOICES = [
        ('vpn', 'VPN'), ('remoto', 'Acesso remoto assistido'),
        ('ambos', 'VPN e acesso remoto'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'), ('aprovada', 'Aprovada'),
        ('em_configuracao', 'Em configuração'), ('ativa', 'Ativa'),
        ('encerrada', 'Encerrada'), ('reprovada', 'Reprovada'),
        ('cancelada', 'Cancelada'),
    ]

    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='solicitacoes_vpn')
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name='solicitacoes_vpn')
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='solicitacoes_vpn_abertas',
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitacoes_vpn_atendidas',
    )
    nome = models.CharField(max_length=180)
    cpf = models.CharField(max_length=11)
    email = models.EmailField()
    telefone = models.CharField(max_length=30, blank=True)
    vinculo = models.CharField(max_length=20, choices=VINCULO_CHOICES)
    empresa_terceira = models.CharField(max_length=180, blank=True)
    tipo_acesso = models.CharField(max_length=20, choices=TIPO_CHOICES)
    equipamento = models.CharField(max_length=180, help_text='Patrimônio ou identificação do equipamento.')
    sistema_destino = models.CharField(max_length=255, help_text='Sistemas ou equipamentos que serão acessados.')
    finalidade = models.TextField()
    inicio_validade = models.DateTimeField()
    fim_validade = models.DateTimeField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendente')
    observacao_ti = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    encerrado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Solicitação de acesso remoto'
        verbose_name_plural = 'Solicitações de acesso remoto'

    def __str__(self):
        return f'#{self.pk} - {self.nome}'


class HistoricoAcessoRemoto(models.Model):
    solicitacao = models.ForeignKey(
        SolicitacaoAcessoRemoto, on_delete=models.CASCADE, related_name='historico',
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status_anterior = models.CharField(max_length=30, blank=True)
    status_novo = models.CharField(max_length=30)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']


def caminho_anexo(instance, filename):
    return f'acesso_remoto/{instance.solicitacao_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class AnexoAcessoRemoto(models.Model):
    solicitacao = models.ForeignKey(
        SolicitacaoAcessoRemoto, on_delete=models.CASCADE, related_name='anexos',
    )
    arquivo = models.FileField(upload_to=caminho_anexo)
    nome_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=150, default='application/octet-stream')
    tamanho = models.PositiveBigIntegerField(default=0)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']
