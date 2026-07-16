from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models

from usuarios.models import Unidade


class ExameLaboratorial(models.Model):
    CATEGORIA_CHOICES = [
        ('bioquimica', 'Bioquímica'), ('hematologia', 'Hematologia'),
        ('microbiologia', 'Microbiologia'), ('imunologia', 'Imunologia'),
        ('urinanalise', 'Urinálise'), ('parasitologia', 'Parasitologia'),
        ('genetica', 'Genética'), ('outro', 'Outro'),
    ]
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='exames_laboratoriais')
    codigo = models.CharField(max_length=60, blank=True)
    nome = models.CharField(max_length=180)
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES)
    sinonimos = models.CharField(max_length=255, blank=True, help_text='Outros nomes usados na pesquisa.')
    material = models.CharField(max_length=180)
    recipiente = models.CharField(max_length=180, blank=True, help_text='Tubo ou recipiente indicado.')
    volume_minimo = models.CharField(max_length=80, blank=True)
    preparo = models.TextField(blank=True)
    instrucoes_coleta = models.TextField(blank=True)
    conservacao_transporte = models.TextField(blank=True)
    prazo_resultado = models.CharField(max_length=120, blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='exames_criados')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        constraints = [models.UniqueConstraint(fields=['unidade', 'nome'], name='exame_nome_unico_unidade')]

    def __str__(self):
        return self.nome


def caminho_documento(instance, filename):
    return f'laboratorio/{instance.exame_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class DocumentoExame(models.Model):
    exame = models.ForeignKey(ExameLaboratorial, on_delete=models.CASCADE, related_name='documentos')
    arquivo = models.FileField(upload_to=caminho_documento)
    nome_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=150, default='application/octet-stream')
    tamanho = models.PositiveBigIntegerField(default=0)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome_original']
