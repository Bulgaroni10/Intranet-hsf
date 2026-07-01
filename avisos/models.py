from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.utils import timezone

from usuarios.models import Unidade


class AvisoComunicado(models.Model):
    TIPO_CHOICES = [
        ('comunicado', 'Comunicado'),
        ('manutencao', 'Manutenção'),
        ('indisponibilidade', 'Indisponibilidade'),
        ('orientacao', 'Orientação'),
        ('mudanca_fluxo', 'Mudança de fluxo'),
        ('urgente', 'Urgente'),
    ]

    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    titulo = models.CharField(max_length=180)

    tipo = models.CharField(
        max_length=40,
        choices=TIPO_CHOICES,
        default='comunicado'
    )

    prioridade = models.CharField(
        max_length=40,
        choices=PRIORIDADE_CHOICES,
        default='normal'
    )

    resumo = models.CharField(
        max_length=220,
        blank=True,
        help_text='Resumo curto para aparecer no portal.'
    )

    mensagem = models.TextField(
        help_text='Mensagem completa do comunicado.'
    )

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='avisos_comunicados',
        help_text='Deixe em branco para comunicado geral, válido para todas as unidades.'
    )

    unidades_compartilhadas = models.ManyToManyField(
        Unidade,
        blank=True,
        related_name='avisos_compartilhados',
        help_text='Use para compartilhar o aviso com outras unidades específicas.'
    )

    grupos_permitidos = models.ManyToManyField(
        Group,
        blank=True,
        related_name='avisos_comunicados',
        help_text='Se não selecionar grupos, aparece para todos os usuários logados.'
    )

    link_externo = models.URLField(
        blank=True,
        help_text='Opcional: link relacionado ao aviso.'
    )

    arquivo = models.FileField(
        upload_to='avisos/%Y/%m/',
        blank=True,
        null=True,
        help_text='Opcional: anexo relacionado ao comunicado.'
    )

    fixar_no_topo = models.BooleanField(
        default=False,
        help_text='Avisos fixados aparecem primeiro.'
    )

    exibir_no_dashboard = models.BooleanField(
        default=True,
        help_text='Exibe este aviso na tela inicial do portal.'
    )

    ativo = models.BooleanField(default=True)

    publicado_em = models.DateTimeField(default=timezone.now)

    expira_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Opcional. Após essa data, o aviso deixa de aparecer.'
    )

    criado_por = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='avisos_criados'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Aviso / comunicado'
        verbose_name_plural = 'Avisos / comunicados'
        ordering = [
            '-fixar_no_topo',
            '-prioridade',
            '-publicado_em',
            'titulo',
        ]

    def __str__(self):
        unidade = self.unidade.sigla if self.unidade else 'Geral'
        return f'{unidade} - {self.titulo}'

    @property
    def esta_expirado(self):
        if not self.expira_em:
            return False

        return timezone.now() > self.expira_em

    @property
    def destino_exibicao(self):
        if not self.unidade:
            return 'Geral / Todas as unidades'

        unidades = [self.unidade.sigla]

        for unidade in self.unidades_compartilhadas.all():
            if unidade.sigla not in unidades:
                unidades.append(unidade.sigla)

        return ', '.join(unidades)