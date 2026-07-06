from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from usuarios.models import Unidade, Setor


class SolicitacaoTI(models.Model):
    MODULO_ORIGEM_CHOICES = [
        ('portal', 'Portal'),
        ('mv', 'MV / Sistema Hospitalar'),
        ('base_conhecimento', 'Base de Conhecimento'),
        ('documentos', 'Documentos / Protocolos'),
        ('manuais', 'Manuais e Procedimentos'),
        ('avisos', 'Avisos / Comunicados'),
        ('ramais', 'Ramais e Contatos'),
        ('status_sistemas', 'Status dos Sistemas'),
        ('conversas', 'Conversas Internas'),
        ('administracao', 'Administração da Intranet'),
        ('outros', 'Outros'),
    ]

    TIPO_CHOICES = [
        ('acesso', 'Acesso / Permissão'),
        ('sistema', 'Sistema'),
        ('mv', 'MV / Sistema Hospitalar'),
        ('pep', 'PEP / Prontuário Eletrônico'),
        ('idce', 'IDCE / Laudos'),
        ('impressora', 'Impressora'),
        ('rede', 'Rede / Internet / Wi-Fi'),
        ('ramal', 'Ramal / Telefonia'),
        ('equipamento', 'Equipamento'),
        ('email', 'E-mail'),
        ('outro', 'Outro'),
    ]

    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    STATUS_CHOICES = [
        ('aberto', 'Aberto'),
        ('em_atendimento', 'Em atendimento'),
        ('aguardando_usuario', 'Aguardando usuário'),
        ('aguardando_terceiro', 'Aguardando terceiro'),
        ('resolvido', 'Resolvido'),
        ('cancelado', 'Cancelado'),
    ]

    SLA_STATUS_CHOICES = [
        ('dentro_prazo', 'Dentro do prazo'),
        ('proximo_vencimento', 'Próximo do vencimento'),
        ('estourado', 'SLA estourado'),
        ('encerrado', 'Encerrado'),
        ('sem_sla', 'Sem SLA'),
    ]

    titulo = models.CharField(max_length=180)

    modulo_origem = models.CharField(
        max_length=60,
        choices=MODULO_ORIGEM_CHOICES,
        default='portal',
        help_text='Módulo da intranet onde o chamado foi aberto.'
    )

    tipo = models.CharField(max_length=40, choices=TIPO_CHOICES, default='outro')
    prioridade = models.CharField(max_length=40, choices=PRIORIDADE_CHOICES, default='normal')
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='aberto')

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_ti'
    )

    setor = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_ti'
    )

    solicitante = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_ti_abertas'
    )

    responsavel_ti = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_ti_responsavel'
    )

    descricao = models.TextField()
    equipamento = models.CharField(max_length=160, blank=True)

    anexo = models.FileField(
        upload_to='solicitacoes_ti/%Y/%m/',
        blank=True,
        null=True
    )

    resposta_ti = models.TextField(blank=True)

    visto_pela_ti = models.BooleanField(default=False)
    visto_pela_ti_em = models.DateTimeField(null=True, blank=True)

    conversa_iniciada = models.BooleanField(default=False)
    conversa_iniciada_em = models.DateTimeField(null=True, blank=True)

    sla_horas = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Prazo de SLA em horas, calculado pela prioridade.'
    )

    sla_prazo_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Data e hora limite para atendimento conforme SLA.'
    )

    sla_status = models.CharField(
        max_length=40,
        choices=SLA_STATUS_CHOICES,
        default='sem_sla'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    resolvido_em = models.DateTimeField(null=True, blank=True)

    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Solicitação interna de TI'
        verbose_name_plural = 'Solicitações internas de TI'
        ordering = ['-criado_em']

    def __str__(self):
        return f'#{self.id} - {self.titulo}'

    @property
    def esta_encerrada(self):
        return self.status in ['resolvido', 'cancelado']

    @property
    def modulo_origem_exibicao(self):
        mapa = dict(self.MODULO_ORIGEM_CHOICES)
        return mapa.get(self.modulo_origem, 'Portal')

    @property
    def modulo_origem_icone(self):
        mapa = {
            'portal': '🏠',
            'mv': '🏥',
            'base_conhecimento': '📚',
            'documentos': '📄',
            'manuais': '📘',
            'avisos': '📢',
            'ramais': '☎️',
            'status_sistemas': '📊',
            'conversas': '💬',
            'administracao': '⚙️',
            'outros': '🎫',
        }

        return mapa.get(self.modulo_origem, '🎫')

    @property
    def sla_status_exibicao(self):
        mapa = {
            'dentro_prazo': 'Dentro do prazo',
            'proximo_vencimento': 'Próximo do vencimento',
            'estourado': 'SLA estourado',
            'encerrado': 'Encerrado',
            'sem_sla': 'Sem SLA',
        }

        return mapa.get(self.sla_status, 'Sem SLA')

    @property
    def sla_classe_css(self):
        mapa = {
            'dentro_prazo': 'sla-ok',
            'proximo_vencimento': 'sla-alerta',
            'estourado': 'sla-estourado',
            'encerrado': 'sla-encerrado',
            'sem_sla': 'sla-sem',
        }

        return mapa.get(self.sla_status, 'sla-sem')

    @property
    def sla_icone(self):
        mapa = {
            'dentro_prazo': '✅',
            'proximo_vencimento': '⚠️',
            'estourado': '🚨',
            'encerrado': '🏁',
            'sem_sla': '➖',
        }

        return mapa.get(self.sla_status, '➖')

    @property
    def tempo_restante_sla(self):
        if not self.sla_prazo_em:
            return 'Sem prazo definido'

        if self.esta_encerrada:
            return 'Chamado encerrado'

        agora = timezone.now()
        diferenca = self.sla_prazo_em - agora

        total_segundos = int(diferenca.total_seconds())

        if total_segundos <= 0:
            atraso = abs(total_segundos)
            horas = atraso // 3600
            minutos = (atraso % 3600) // 60

            if horas > 0:
                return f'Estourado há {horas}h {minutos}min'

            return f'Estourado há {minutos}min'

        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60

        if horas > 0:
            return f'Restam {horas}h {minutos}min'

        return f'Restam {minutos}min'

    @staticmethod
    def obter_horas_sla_por_prioridade(prioridade):
        mapa = {
            'critica': 2,
            'alta': 4,
            'normal': 24,
            'baixa': 48,
        }

        return mapa.get(prioridade, 24)

    def calcular_sla_status(self):
        if not self.sla_prazo_em:
            return 'sem_sla'

        if self.esta_encerrada:
            return 'encerrado'

        agora = timezone.now()

        if agora > self.sla_prazo_em:
            return 'estourado'

        total_segundos = (self.sla_prazo_em - agora).total_seconds()
        total_horas = total_segundos / 3600

        if total_horas <= 1:
            return 'proximo_vencimento'

        return 'dentro_prazo'

    def atualizar_sla(self, salvar=True):
        horas_sla = self.obter_horas_sla_por_prioridade(self.prioridade)

        self.sla_horas = horas_sla

        if self.criado_em:
            self.sla_prazo_em = self.criado_em + timezone.timedelta(hours=horas_sla)

        self.sla_status = self.calcular_sla_status()

        if salvar and self.pk:
            SolicitacaoTI.objects.filter(pk=self.pk).update(
                sla_horas=self.sla_horas,
                sla_prazo_em=self.sla_prazo_em,
                sla_status=self.sla_status,
            )

    def save(self, *args, **kwargs):
        criando = self.pk is None

        super().save(*args, **kwargs)

        precisa_atualizar_sla = False

        horas_sla = self.obter_horas_sla_por_prioridade(self.prioridade)

        if self.sla_horas != horas_sla:
            self.sla_horas = horas_sla
            precisa_atualizar_sla = True

        if not self.sla_prazo_em and self.criado_em:
            self.sla_prazo_em = self.criado_em + timezone.timedelta(hours=horas_sla)
            precisa_atualizar_sla = True

        novo_status_sla = self.calcular_sla_status()

        if self.sla_status != novo_status_sla:
            self.sla_status = novo_status_sla
            precisa_atualizar_sla = True

        if criando or precisa_atualizar_sla:
            SolicitacaoTI.objects.filter(pk=self.pk).update(
                sla_horas=self.sla_horas,
                sla_prazo_em=self.sla_prazo_em,
                sla_status=self.sla_status,
            )

    def marcar_como_vista(self, usuario_ti=None):
        self.visto_pela_ti = True
        self.visto_pela_ti_em = timezone.now()

        if usuario_ti and not self.responsavel_ti:
            self.responsavel_ti = usuario_ti

        if self.status == 'aberto':
            self.status = 'em_atendimento'

        self.save()

    def iniciar_conversa(self, usuario_ti=None):
        self.conversa_iniciada = True
        self.conversa_iniciada_em = timezone.now()
        self.visto_pela_ti = True

        if not self.visto_pela_ti_em:
            self.visto_pela_ti_em = timezone.now()

        if usuario_ti and not self.responsavel_ti:
            self.responsavel_ti = usuario_ti

        if self.status == 'aberto':
            self.status = 'em_atendimento'

        self.save()

    def marcar_resolvida(self):
        self.status = 'resolvido'
        self.resolvido_em = timezone.now()
        self.save()


class MensagemSolicitacaoTI(models.Model):
    ORIGEM_CHOICES = [
        ('ti', 'TI'),
        ('solicitante', 'Solicitante'),
        ('sistema', 'Sistema'),
    ]

    solicitacao = models.ForeignKey(
        SolicitacaoTI,
        on_delete=models.CASCADE,
        related_name='mensagens'
    )

    autor = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensagens_solicitacoes_ti'
    )

    origem = models.CharField(
        max_length=30,
        choices=ORIGEM_CHOICES,
        default='sistema'
    )

    mensagem = models.TextField()

    criado_em = models.DateTimeField(auto_now_add=True)

    lida_pela_ti = models.BooleanField(default=False)
    lida_pelo_solicitante = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Mensagem da solicitação de TI'
        verbose_name_plural = 'Mensagens das solicitações de TI'
        ordering = ['criado_em']

    def __str__(self):
        return f'Mensagem #{self.id} - Solicitação #{self.solicitacao_id}'