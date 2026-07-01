from django.db import models

from usuarios.models import Unidade


class RamalContato(models.Model):
    TIPO_CHOICES = [
        ('setor', 'Setor'),
        ('pessoa', 'Pessoa'),
        ('servico', 'Serviço'),
        ('emergencia', 'Emergência / Crítico'),
    ]

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ramais_contatos',
        help_text='Deixe em branco para contato geral, válido para todas as unidades.'
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        default='setor'
    )

    setor = models.CharField(
        max_length=120,
        blank=True,
        help_text='Ex: TI, Recepção, Faturamento, Centro Cirúrgico.'
    )

    nome = models.CharField(
        max_length=160,
        help_text='Nome do setor, pessoa ou serviço.'
    )

    cargo_funcao = models.CharField(
        max_length=120,
        blank=True,
        help_text='Ex: Coordenador, Analista, Recepção, Plantão.'
    )

    ramal = models.CharField(
        max_length=30,
        blank=True
    )

    telefone = models.CharField(
        max_length=40,
        blank=True
    )

    celular = models.CharField(
        max_length=40,
        blank=True
    )

    whatsapp = models.CharField(
        max_length=40,
        blank=True,
        help_text='Informe somente se for diferente do celular.'
    )

    email = models.EmailField(
        blank=True
    )

    localizacao = models.CharField(
        max_length=160,
        blank=True,
        help_text='Ex: 1º andar, Recepção principal, Sala TI.'
    )

    observacao = models.TextField(
        blank=True
    )

    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ramal e contato'
        verbose_name_plural = 'Ramais e contatos'
        ordering = [
            'unidade__nome',
            'setor',
            'ordem',
            'nome',
        ]

    def __str__(self):
        unidade = self.unidade.sigla if self.unidade else 'Geral'

        if self.ramal:
            return f'{unidade} - {self.nome} - Ramal {self.ramal}'

        return f'{unidade} - {self.nome}'

    @property
    def whatsapp_para_link(self):
        numero = self.whatsapp or self.celular

        if not numero:
            return ''

        somente_numeros = ''.join(caractere for caractere in numero if caractere.isdigit())

        if not somente_numeros:
            return ''

        if len(somente_numeros) in [10, 11]:
            somente_numeros = f'55{somente_numeros}'

        return somente_numeros