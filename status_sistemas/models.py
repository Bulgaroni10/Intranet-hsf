from django.db import models

from usuarios.models import Unidade


class SistemaMonitorado(models.Model):
    CATEGORIA_CHOICES = [
        ('assistencial', 'Assistencial'),
        ('administrativo', 'Administrativo'),
        ('infraestrutura', 'Infraestrutura'),
        ('terceiro', 'Fornecedor / Terceiro'),
    ]

    nome = models.CharField(
        max_length=120,
        unique=True
    )

    descricao = models.CharField(
        max_length=180,
        blank=True
    )

    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_CHOICES
    )

    icone = models.CharField(
        max_length=10,
        default='🖥️'
    )

    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sistema monitorado'
        verbose_name_plural = 'Sistemas monitorados'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class OcorrenciaSistema(models.Model):
    STATUS_CHOICES = [
        ('operacional', 'Operacional'),
        ('instavel', 'Instável'),
        ('indisponivel', 'Indisponível'),
        ('manutencao', 'Manutenção'),
    ]

    IMPACTO_CHOICES = [
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('alto', 'Alto'),
        ('critico', 'Crítico'),
    ]

    sistema = models.ForeignKey(
        SistemaMonitorado,
        on_delete=models.CASCADE,
        related_name='ocorrencias'
    )

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ocorrencias_sistemas',
        help_text='Deixe em branco para ocorrência geral, válida para todas as unidades.'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='operacional'
    )

    impacto = models.CharField(
        max_length=30,
        choices=IMPACTO_CHOICES,
        default='baixo'
    )

    titulo = models.CharField(max_length=160)

    mensagem = models.TextField(
        blank=True,
        help_text='Mensagem que será exibida aos usuários no portal.'
    )

    previsao = models.CharField(
        max_length=120,
        blank=True,
        help_text='Ex: Sem previsão, Em acompanhamento, Previsão 14h.'
    )

    acao_ti = models.TextField(
        blank=True,
        help_text='Informação interna da TI sobre a atuação.'
    )

    causa_raiz = models.TextField(
        blank=True,
        help_text='Causa raiz identificada no encerramento da ocorrência.'
    )

    solucao_aplicada = models.TextField(
        blank=True,
        help_text='Solução aplicada para normalização do ambiente.'
    )

    observacao_encerramento = models.TextField(
        blank=True,
        help_text='Observação final do encerramento.'
    )

    ativo = models.BooleanField(
        default=True,
        help_text='Somente ocorrências ativas aparecem no portal.'
    )

    aberto_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    encerrado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Ocorrência de sistema'
        verbose_name_plural = 'Ocorrências de sistemas'
        ordering = ['-ativo', '-atualizado_em']

    def __str__(self):
        unidade = self.unidade.sigla if self.unidade else 'Geral'
        return f'{self.sistema.nome} - {unidade} - {self.get_status_display()}'