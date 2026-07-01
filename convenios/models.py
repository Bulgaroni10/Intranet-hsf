from django.conf import settings
from django.db import models

from usuarios.models import Unidade


class Convenio(models.Model):
    codigo_mv = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text='Código do convênio no MV.'
    )

    nome = models.CharField(max_length=120, unique=True)

    tipo_mv = models.CharField(
        max_length=80,
        blank=True,
        help_text='Tipo informado no relatório do MV. Ex: CONVENIO, PARTICULAR.'
    )

    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Convênio'
        verbose_name_plural = 'Convênios'
        ordering = ['nome']

    def __str__(self):
        if self.codigo_mv:
            return f'{self.nome} [{self.codigo_mv}]'
        return self.nome


class PlanoConvenio(models.Model):
    convenio = models.ForeignKey(
        Convenio,
        on_delete=models.CASCADE,
        related_name='planos'
    )

    codigo_mv = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text='Código do plano no MV.'
    )

    nome = models.CharField(max_length=120)

    regra_codigo_mv = models.CharField(
        max_length=30,
        blank=True,
        help_text='Código da regra no MV.'
    )

    regra_nome_mv = models.CharField(
        max_length=160,
        blank=True,
        help_text='Nome da regra no MV.'
    )

    indice_codigo_mv = models.CharField(
        max_length=30,
        blank=True,
        help_text='Código do índice no MV.'
    )

    indice_nome_mv = models.CharField(
        max_length=160,
        blank=True,
        help_text='Nome do índice no MV.'
    )

    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plano do convênio'
        verbose_name_plural = 'Planos dos convênios'
        ordering = ['convenio__nome', 'nome', 'codigo_mv']

    def __str__(self):
        codigo = f' [{self.codigo_mv}]' if self.codigo_mv else ''
        return f'{self.convenio.nome} - {self.nome}{codigo}'


class Especialidade(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Especialidade'
        verbose_name_plural = 'Especialidades'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class RegraAtendimentoConvenio(models.Model):
    TIPO_ATENDIMENTO_CHOICES = [
        ('consulta', 'Consulta'),
        ('pronto_atendimento', 'Pronto Atendimento'),
        ('exame', 'Exame'),
        ('internacao', 'Internação'),
        ('cirurgia', 'Cirurgia'),
        ('terapia', 'Terapia'),
        ('pediatria', 'Pediatria'),
    ]

    STATUS_CHOICES = [
        ('aceito', 'Aceito'),
        ('nao_aceito', 'Não aceito'),
        ('consultar_autorizacao', 'Consultar autorização'),
        ('suspenso', 'Suspenso temporariamente'),
    ]

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.CASCADE,
        related_name='regras_convenios'
    )

    convenio = models.ForeignKey(
        Convenio,
        on_delete=models.CASCADE,
        related_name='regras'
    )

    plano = models.ForeignKey(
        PlanoConvenio,
        on_delete=models.CASCADE,
        related_name='regras'
    )

    tipo_atendimento = models.CharField(
        max_length=40,
        choices=TIPO_ATENDIMENTO_CHOICES
    )

    especialidade = models.ForeignKey(
        Especialidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='regras',
        help_text='Preencha quando a regra depender de especialidade. Ex: Ortopedia.'
    )

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default='aceito'
    )

    exige_autorizacao = models.BooleanField(default=False)

    observacao = models.TextField(blank=True)

    ativo = models.BooleanField(default=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Regra de atendimento do convênio'
        verbose_name_plural = 'Regras de atendimento dos convênios'
        ordering = [
            'unidade__nome',
            'convenio__nome',
            'plano__nome',
            'tipo_atendimento',
            'especialidade__nome',
        ]

    def __str__(self):
        especialidade = self.especialidade.nome if self.especialidade else 'Geral'
        return f'{self.unidade.sigla} - {self.convenio.nome} - {self.plano.nome} - {self.get_tipo_atendimento_display()} - {especialidade}'


class ProcedimentoProibidoPlano(models.Model):
    convenio = models.ForeignKey(
        Convenio,
        on_delete=models.CASCADE,
        related_name='procedimentos_proibidos'
    )

    plano = models.ForeignKey(
        PlanoConvenio,
        on_delete=models.CASCADE,
        related_name='procedimentos_proibidos'
    )

    codigo_procedimento = models.CharField(
        max_length=30,
        db_index=True
    )

    descricao_procedimento = models.CharField(
        max_length=255,
        db_index=True
    )

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Procedimento proibido do plano'
        verbose_name_plural = 'Procedimentos proibidos dos planos'
        ordering = [
            'convenio__nome',
            'plano__nome',
            'descricao_procedimento',
        ]
        unique_together = (
            'plano',
            'codigo_procedimento',
        )

    def __str__(self):
        return f'{self.convenio.nome} - {self.plano.nome} - {self.codigo_procedimento} - {self.descricao_procedimento}'


class ImportacaoMV(models.Model):
    TIPO_CHOICES = [
        ('convenios_planos', 'Convênios e planos'),
        ('procedimentos_proibidos', 'Procedimentos proibidos'),
        ('regras_atendimento', 'Regras de atendimento'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('concluida', 'Concluída'),
        ('concluida_com_erros', 'Concluída com erros'),
        ('erro', 'Erro'),
    ]

    tipo = models.CharField(
        max_length=40,
        choices=TIPO_CHOICES
    )

    arquivo = models.FileField(
        upload_to='importacoes_mv/%Y/%m/',
        help_text='Arquivo CSV ou XLSX para importação.'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pendente'
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='importacoes_mv'
    )

    total_linhas = models.PositiveIntegerField(default=0)
    total_sucesso = models.PositiveIntegerField(default=0)
    total_erros = models.PositiveIntegerField(default=0)

    mensagem = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Importação MV'
        verbose_name_plural = 'Importações MV'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.get_status_display()} - {self.criado_em.strftime("%d/%m/%Y %H:%M")}'

    @property
    def possui_erros(self):
        return self.total_erros > 0

    @property
    def percentual_sucesso(self):
        if self.total_linhas == 0:
            return 0

        return round((self.total_sucesso / self.total_linhas) * 100, 2)


class ItemImportacaoMV(models.Model):
    STATUS_CHOICES = [
        ('sucesso', 'Sucesso'),
        ('erro', 'Erro'),
        ('ignorado', 'Ignorado'),
    ]

    importacao = models.ForeignKey(
        ImportacaoMV,
        on_delete=models.CASCADE,
        related_name='itens'
    )

    linha = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    mensagem = models.TextField(blank=True)
    dados = models.JSONField(default=dict, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item da importação MV'
        verbose_name_plural = 'Itens da importação MV'
        ordering = ['importacao', 'linha']

    def __str__(self):
        return f'Linha {self.linha} - {self.get_status_display()}'