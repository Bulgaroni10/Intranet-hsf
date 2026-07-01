from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.utils import timezone

from usuarios.models import Unidade, Setor


class DocumentoProtocolo(models.Model):
    TIPO_CHOICES = [
        ('pop', 'POP'),
        ('protocolo', 'Protocolo'),
        ('politica', 'Política interna'),
        ('norma', 'Norma'),
        ('manual', 'Manual'),
        ('formulario', 'Formulário'),
        ('fluxo', 'Fluxo'),
        ('plano_contingencia', 'Plano de contingência'),
        ('documento_institucional', 'Documento institucional'),
        ('outro', 'Outro'),
    ]

    CATEGORIA_CHOICES = [
        ('assistencial', 'Assistencial'),
        ('administrativo', 'Administrativo'),
        ('qualidade', 'Qualidade / ONA'),
        ('ti', 'Tecnologia da Informação'),
        ('operacional', 'Operacional'),
        ('rh', 'Recursos Humanos'),
        ('financeiro', 'Financeiro'),
        ('farmacia', 'Farmácia'),
        ('enfermagem', 'Enfermagem'),
        ('corpo_clinico', 'Corpo Clínico'),
        ('outro', 'Outro'),
    ]

    STATUS_CHOICES = [
        ('vigente', 'Vigente'),
        ('em_revisao', 'Em revisão'),
        ('vencido', 'Vencido'),
        ('obsoleto', 'Obsoleto'),
        ('substituido', 'Substituído'),
        ('inativo', 'Inativo'),
    ]

    codigo = models.CharField(
        max_length=60,
        blank=True,
        help_text='Ex: POP-TI-001, PROT-ENF-002.'
    )

    titulo = models.CharField(max_length=200)

    tipo = models.CharField(
        max_length=40,
        choices=TIPO_CHOICES,
        default='pop'
    )

    categoria = models.CharField(
        max_length=40,
        choices=CATEGORIA_CHOICES,
        default='assistencial'
    )

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_protocolos',
        help_text='Deixe em branco para documento geral, válido para todas as unidades.'
    )

    unidades_compartilhadas = models.ManyToManyField(
        Unidade,
        blank=True,
        related_name='documentos_compartilhados',
        help_text='Use para compartilhar o documento com outras unidades específicas.'
    )

    setor = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_protocolos',
        help_text='Opcional. Use para vincular o documento a um setor.'
    )

    descricao = models.TextField(blank=True)

    arquivo = models.FileField(
        upload_to='documentos/%Y/%m/',
        help_text='Anexe o documento em PDF, DOCX, XLSX ou outro formato permitido.'
    )

    versao = models.CharField(
        max_length=30,
        blank=True,
        help_text='Ex: 1.0, 2.1, revisão 03.'
    )

    responsavel = models.CharField(
        max_length=160,
        blank=True,
        help_text='Responsável pelo documento.'
    )

    data_publicacao = models.DateField(
        default=timezone.localdate
    )

    data_validade = models.DateField(
        null=True,
        blank=True,
        help_text='Opcional. Usado para controle de vencimento.'
    )

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default='vigente'
    )

    exibir_no_dashboard = models.BooleanField(
        default=False,
        help_text='Exibe no dashboard quando estiver próximo do vencimento ou em revisão.'
    )

    grupos_permitidos = models.ManyToManyField(
        Group,
        blank=True,
        related_name='documentos_protocolos',
        help_text='Se não selecionar grupos, aparece para todos os usuários logados.'
    )

    leitura_obrigatoria = models.BooleanField(
        default=False,
        help_text='Reservado para controle futuro de leitura obrigatória.'
    )

    ativo = models.BooleanField(default=True)

    criado_por = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_criados'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Documento / Protocolo'
        verbose_name_plural = 'Documentos / Protocolos'
        ordering = ['categoria', 'tipo', 'titulo']

    def __str__(self):
        if self.codigo:
            return f'{self.codigo} - {self.titulo}'

        return self.titulo

    @property
    def esta_vencido(self):
        if not self.data_validade:
            return False

        return self.data_validade < timezone.localdate()

    @property
    def dias_para_vencer(self):
        if not self.data_validade:
            return None

        return (self.data_validade - timezone.localdate()).days

    @property
    def proximo_do_vencimento(self):
        dias = self.dias_para_vencer

        if dias is None:
            return False

        return 0 <= dias <= 30

    @property
    def destino_exibicao(self):
        if not self.unidade:
            return 'Geral / Todas as unidades'

        unidades = [self.unidade.sigla]

        for unidade in self.unidades_compartilhadas.all():
            if unidade.sigla not in unidades:
                unidades.append(unidade.sigla)

        return ', '.join(unidades)