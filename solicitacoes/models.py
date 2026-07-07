from django.conf import settings
from django.db import models
from django.utils import timezone


class CategoriaSolicitacao(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoria de Solicitação'
        verbose_name_plural = 'Categorias de Solicitações'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class SolicitacaoInterna(models.Model):
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('em_andamento', 'Em andamento'),
        ('aguardando', 'Aguardando'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]

    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    titulo = models.CharField(max_length=180)
    descricao = models.TextField()

    categoria = models.ForeignKey(
        CategoriaSolicitacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes'
    )

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_abertas'
    )

    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_responsavel'
    )

    unidade = models.ForeignKey(
        'usuarios.Unidade',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    setor = models.ForeignKey(
        'usuarios.Setor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='aberta')
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='media')

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitação Interna'
        verbose_name_plural = 'Solicitações Internas'
        ordering = ['-criado_em']

    def save(self, *args, **kwargs):
        if self.status == 'concluida' and not self.concluido_em:
            self.concluido_em = timezone.now()

        if self.status != 'concluida':
            self.concluido_em = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f'#{self.id} - {self.titulo}'


class ComentarioSolicitacao(models.Model):
    solicitacao = models.ForeignKey(
        SolicitacaoInterna,
        on_delete=models.CASCADE,
        related_name='comentarios'
    )

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    mensagem = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Comentário da Solicitação'
        verbose_name_plural = 'Comentários das Solicitações'
        ordering = ['criado_em']

    def __str__(self):
        return f'Comentário #{self.id}'


class HistoricoSolicitacao(models.Model):
    TIPO_CHOICES = [
        ('criacao', 'Criação'),
        ('status', 'Status'),
        ('prioridade', 'Prioridade'),
        ('responsavel', 'Responsável'),
        ('comentario', 'Comentário'),
        ('atualizacao', 'Atualização'),
        ('conclusao', 'Conclusão'),
    ]

    solicitacao = models.ForeignKey(
        SolicitacaoInterna,
        on_delete=models.CASCADE,
        related_name='historicos'
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=160)
    descricao = models.TextField(blank=True)

    valor_anterior = models.CharField(max_length=255, blank=True)
    valor_novo = models.CharField(max_length=255, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico da Solicitação'
        verbose_name_plural = 'Históricos das Solicitações'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.get_tipo_display()} - #{self.solicitacao_id}'