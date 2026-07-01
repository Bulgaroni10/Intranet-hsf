from django.conf import settings
from django.db import models
from django.contrib.auth.models import Group

from usuarios.models import Unidade, Setor


class CategoriaConhecimento(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Categoria da base de conhecimento'
        verbose_name_plural = 'Categorias da base de conhecimento'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class DocumentoConhecimento(models.Model):
    STATUS_CHOICES = [
        ('vigente', 'Vigente'),
        ('em_revisao', 'Em revisão'),
        ('obsoleto', 'Obsoleto'),
        ('rascunho', 'Rascunho'),
    ]

    TIPO_CHOICES = [
        ('pop', 'POP'),
        ('manual', 'Manual'),
        ('orientacao', 'Orientação'),
        ('politica', 'Política'),
        ('fluxo', 'Fluxo'),
        ('treinamento', 'Treinamento'),
        ('outro', 'Outro'),
    ]

    titulo = models.CharField(max_length=180)

    tipo = models.CharField(
        max_length=40,
        choices=TIPO_CHOICES,
        default='pop'
    )

    categoria = models.ForeignKey(
        CategoriaConhecimento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos'
    )

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_conhecimento',
        help_text='Deixe em branco para disponibilizar para todas as unidades.'
    )

    setor = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_conhecimento',
        help_text='Deixe em branco para disponibilizar para todos os setores.'
    )

    descricao = models.TextField(blank=True)

    arquivo = models.FileField(
        upload_to='base_conhecimento/%Y/%m/',
        blank=True,
        null=True
    )

    link_externo = models.URLField(blank=True)

    versao = models.CharField(
        max_length=30,
        blank=True,
        default='1.0'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='vigente'
    )

    leitura_obrigatoria = models.BooleanField(default=False)

    responsavel_revisao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_revisao'
    )

    data_revisao = models.DateField(
        null=True,
        blank=True,
        help_text='Data prevista ou realizada da revisão.'
    )

    grupos_permitidos = models.ManyToManyField(
        Group,
        blank=True,
        related_name='documentos_conhecimento_permitidos'
    )

    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_conhecimento_criados'
    )

    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_conhecimento_atualizados'
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Documento da base de conhecimento'
        verbose_name_plural = 'Documentos da base de conhecimento'
        ordering = [
            'ordem',
            'categoria__nome',
            'setor__nome',
            'titulo',
        ]

    def __str__(self):
        return self.titulo

    @property
    def destino_exibicao(self):
        partes = []

        if self.unidade:
            partes.append(self.unidade.sigla)
        else:
            partes.append('Todas as unidades')

        if self.setor:
            partes.append(self.setor.nome)
        else:
            partes.append('Todos os setores')

        return ' • '.join(partes)

    @property
    def possui_arquivo_ou_link(self):
        return bool(self.arquivo or self.link_externo)


class LeituraDocumentoConhecimento(models.Model):
    documento = models.ForeignKey(
        DocumentoConhecimento,
        on_delete=models.CASCADE,
        related_name='leituras'
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leituras_documentos_conhecimento'
    )

    unidade_usuario = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leituras_base_conhecimento'
    )

    setor_usuario = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leituras_base_conhecimento'
    )

    versao_documento = models.CharField(
        max_length=30,
        blank=True
    )

    confirmado_em = models.DateTimeField(auto_now_add=True)

    ip_origem = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Confirmação de leitura'
        verbose_name_plural = 'Confirmações de leitura'
        ordering = ['-confirmado_em']
        unique_together = ('documento', 'usuario', 'versao_documento')

    def __str__(self):
        return f'{self.usuario} leu {self.documento} - versão {self.versao_documento}'