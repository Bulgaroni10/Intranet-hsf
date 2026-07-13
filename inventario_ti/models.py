from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from usuarios.models import Setor, Unidade


class ComputadorInventario(models.Model):
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    hostname = models.CharField(max_length=120)
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
        constraints = [
            models.UniqueConstraint(fields=["unidade", "hostname"], name="uniq_computador_unidade_hostname"),
        ]

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
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
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


class PatrimonioTI(models.Model):
    TIPO_CHOICES = [
        ("computador", "Computador"),
        ("notebook", "Notebook"),
        ("monitor", "Monitor"),
        ("impressora", "Impressora"),
        ("nobreak", "Nobreak"),
        ("rede", "Rede"),
        ("periferico", "Periférico"),
        ("outro", "Outro"),
    ]

    STATUS_CHOICES = [
        ("em_uso", "Em uso"),
        ("estoque", "Estoque"),
        ("manutencao", "Manutenção"),
        ("baixado", "Baixado"),
        ("extraviado", "Extraviado"),
    ]

    codigo = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="computador")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="em_uso")
    computador = models.OneToOneField(
        ComputadorInventario,
        on_delete=models.SET_NULL,
        related_name="patrimonio_vinculado",
        null=True,
        blank=True,
    )
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True)
    responsavel = models.CharField(max_length=180, blank=True, default="")
    fabricante = models.CharField(max_length=180, blank=True, default="")
    modelo = models.CharField(max_length=180, blank=True, default="")
    serial = models.CharField(max_length=180, blank=True, default="")
    nota_fiscal = models.CharField(max_length=120, blank=True, default="")
    data_aquisicao = models.DateField(null=True, blank=True)
    valor_aquisicao = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    observacao = models.TextField(blank=True, default="")
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patrimônio TI"
        verbose_name_plural = "Patrimônios TI"
        ordering = ["codigo"]
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["tipo", "status"]),
        ]

    def __str__(self):
        return self.codigo


class MovimentacaoPatrimonioTI(models.Model):
    TIPO_CHOICES = [
        ("cadastro", "Cadastro"),
        ("transferencia", "Transferência"),
        ("manutencao", "Manutenção"),
        ("baixa", "Baixa"),
        ("retorno", "Retorno"),
        ("ajuste", "Ajuste"),
    ]

    patrimonio = models.ForeignKey(
        PatrimonioTI,
        on_delete=models.CASCADE,
        related_name="movimentacoes",
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    unidade_origem = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_patrimonio_origem",
    )
    setor_origem = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_patrimonio_origem",
    )
    responsavel_origem = models.CharField(max_length=180, blank=True, default="")
    unidade_destino = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_patrimonio_destino",
    )
    setor_destino = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_patrimonio_destino",
    )
    responsavel_destino = models.CharField(max_length=180, blank=True, default="")
    observacao = models.TextField(blank=True, default="")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação de patrimônio TI"
        verbose_name_plural = "Movimentações de patrimônio TI"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.patrimonio.codigo} - {self.get_tipo_display()}"


class ImpressoraMonitorada(models.Model):
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    ip = models.GenericIPAddressField(unique=True)
    modelo_informado = models.CharField(max_length=180, blank=True, default="")
    modelo_detectado = models.CharField(max_length=180, blank=True, default="")
    local = models.CharField(max_length=180)
    ativo = models.BooleanField(default=True)
    online = models.BooleanField(default=False)
    status_dispositivo = models.CharField(max_length=255, blank=True, default="")
    toner_percentual = models.PositiveSmallIntegerField(null=True, blank=True)
    cilindro_percentual = models.PositiveSmallIntegerField(null=True, blank=True)
    ultimo_erro = models.TextField(blank=True, default="")
    ultima_consulta = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["local", "ip"]
        verbose_name = "Impressora monitorada"
        verbose_name_plural = "Impressoras monitoradas"
        indexes = [models.Index(fields=["unidade", "ativo", "online"])]

    def __str__(self):
        return f"{self.local} - {self.ip}"

    @property
    def modelo(self):
        return self.modelo_detectado or self.modelo_informado

    @property
    def possui_alerta(self):
        texto = self.status_dispositivo.lower()
        termos = ("replace", "substit", "low", "baixo", "error", "erro", "jam", "atol")
        toner_baixo = self.toner_percentual is not None and self.toner_percentual <= 20
        cilindro_baixo = self.cilindro_percentual is not None and self.cilindro_percentual <= 20
        return not self.online or toner_baixo or cilindro_baixo or any(termo in texto for termo in termos)
