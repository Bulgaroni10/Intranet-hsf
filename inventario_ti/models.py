from django.db import models
from django.utils import timezone
from datetime import timedelta


class ComputadorInventario(models.Model):
    hostname = models.CharField(max_length=120, unique=True)
    usuario = models.CharField(max_length=180, blank=True, default="-")

    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    ip_local = models.GenericIPAddressField(null=True, blank=True)
    mac = models.CharField(max_length=50, blank=True, default="-")

    sistema = models.CharField(max_length=180, blank=True, default="-")
    cpu = models.CharField(max_length=255, blank=True, default="-")
    ram = models.CharField(max_length=80, blank=True, default="-")

    disco_total = models.CharField(max_length=80, blank=True, default="-")
    disco_livre = models.CharField(max_length=80, blank=True, default="-")
    disco_percentual = models.CharField(max_length=80, blank=True, default="-")

    fabricante = models.CharField(max_length=180, blank=True, default="-")
    modelo = models.CharField(max_length=180, blank=True, default="-")
    serial = models.CharField(max_length=180, blank=True, default="-")

    patrimonio = models.CharField(max_length=80, blank=True, default="-")
    agent_version = models.CharField(max_length=50, blank=True, default="-")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ultimo_contato = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Computador"
        verbose_name_plural = "Inventário TI"
        ordering = ["hostname"]

    def __str__(self):
        return self.hostname

    @property
    def online(self):
        if not self.ultimo_contato:
            return False

        limite = timezone.now() - timedelta(seconds=90)
        return self.ultimo_contato >= limite

    @property
    def status_texto(self):
        return "ONLINE" if self.online else "OFFLINE"


class HistoricoComputadorInventario(models.Model):
    TIPO_CHOICES = [
        ("cadastro", "Cadastro"),
        ("alteracao", "Alteração"),
        ("heartbeat", "Heartbeat"),
        ("status", "Status"),
    ]

    computador = models.ForeignKey(
        ComputadorInventario,
        on_delete=models.CASCADE,
        related_name="historicos",
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=180)
    descricao = models.TextField(blank=True, default="")
    campo = models.CharField(max_length=80, blank=True, default="")
    valor_anterior = models.TextField(blank=True, default="")
    valor_novo = models.TextField(blank=True, default="")
    dados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico do computador"
        verbose_name_plural = "Histórico do inventário TI"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["computador", "-criado_em"]),
            models.Index(fields=["tipo", "-criado_em"]),
        ]

    def __str__(self):
        return f"{self.computador.hostname} - {self.titulo}"


class ErroAgenteInventario(models.Model):
    computador = models.ForeignKey(
        ComputadorInventario,
        on_delete=models.SET_NULL,
        related_name="erros_agente",
        null=True,
        blank=True,
    )
    hostname = models.CharField(max_length=120)
    agent_version = models.CharField(max_length=50, blank=True, default="-")
    categoria = models.CharField(max_length=80, blank=True, default="geral")
    mensagem = models.TextField()
    detalhe = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Erro do agente"
        verbose_name_plural = "Erros dos agentes"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["hostname", "-criado_em"]),
            models.Index(fields=["categoria", "-criado_em"]),
        ]

    def __str__(self):
        return f"{self.hostname} - {self.categoria}"
