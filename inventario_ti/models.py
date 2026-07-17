from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from usuarios.models import Setor, Unidade
from core.services.uploads import caminho_upload


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


class SuprimentoTI(models.Model):
    ESCOPO_CHOICES = [
        ("ti", "Tecnologia da Informação"),
        ("setorial", "Estoque Setorial"),
    ]
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="suprimentos_ti")
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name="suprimentos_ti", null=True, blank=True)
    escopo = models.CharField(max_length=20, choices=ESCOPO_CHOICES, default="ti")
    codigo = models.CharField(max_length=80)
    nome = models.CharField(max_length=180)
    categoria = models.CharField(max_length=80)
    fabricante = models.CharField(max_length=120, blank=True, default="")
    modelo_compativel = models.CharField(max_length=180, blank=True, default="")
    quantidade = models.PositiveIntegerField(default=0)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estoque_minimo = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["unidade", "setor", "escopo", "codigo"], name="uniq_suprimento_escopo_codigo"),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    @property
    def estoque_baixo(self):
        return self.quantidade <= 5


class MovimentacaoSuprimentoTI(models.Model):
    TIPO_CHOICES = [
        ("entrada", "Entrada"),
        ("saida", "Saída"),
        ("ajuste", "Ajuste"),
    ]

    suprimento = models.ForeignKey(SuprimentoTI, on_delete=models.CASCADE, related_name="movimentacoes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    quantidade = models.PositiveIntegerField()
    saldo_anterior = models.PositiveIntegerField()
    saldo_atual = models.PositiveIntegerField()
    setor_destino = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="consumos_suprimentos_ti")
    impressora_destino = models.CharField(max_length=180, blank=True, default="")
    impressora_monitorada = models.ForeignKey(
        "ImpressoraMonitorada", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consumos_suprimentos",
    )
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    responsavel = models.CharField(max_length=180, blank=True, default="")
    observacao = models.TextField(blank=True, default="")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    estornada_em = models.DateTimeField(null=True, blank=True)
    estornada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes_suprimento_estornadas",
    )
    motivo_estorno = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.suprimento.codigo} - {self.get_tipo_display()} ({self.quantidade})"


class AnexoMovimentacaoSuprimento(models.Model):
    movimentacao = models.ForeignKey(
        MovimentacaoSuprimentoTI, on_delete=models.CASCADE, related_name="anexos",
    )
    arquivo = models.FileField(upload_to=caminho_upload)
    nome_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=150, default="application/octet-stream")
    tamanho = models.PositiveBigIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
        verbose_name = "Anexo da movimentação de suprimento"
        verbose_name_plural = "Anexos das movimentações de suprimentos"

    def __str__(self):
        return self.nome_original


class ImpressoraMonitorada(models.Model):
    SITUACAO_CHOICES = [
        ("estoque", "Em estoque"),
        ("em_uso", "Em uso"),
        ("manutencao", "Em manutenção"),
        ("baixada", "Baixada"),
    ]

    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="impressoras_monitoradas")
    ip = models.GenericIPAddressField(unique=True, null=True, blank=True)
    patrimonio = models.CharField(max_length=80, blank=True, default="")
    numero_serie = models.CharField(max_length=120, blank=True, default="")
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default="em_uso")
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
        return f"{self.local} - {self.ip or 'sem IP'}"

    @property
    def modelo(self):
        return self.modelo_detectado or self.modelo_informado

    @property
    def possui_alerta(self):
        if not self.ativo or not self.ip:
            return False
        texto = self.status_dispositivo.lower()
        termos = ("replace", "substit", "low", "baixo", "error", "erro", "jam", "atol")
        toner_baixo = self.toner_percentual is not None and self.toner_percentual <= 20
        cilindro_baixo = self.cilindro_percentual is not None and self.cilindro_percentual <= 20
        return not self.online or toner_baixo or cilindro_baixo or any(termo in texto for termo in termos)


class MovimentacaoImpressora(models.Model):
    impressora = models.ForeignKey(
        ImpressoraMonitorada, on_delete=models.CASCADE, related_name="movimentacoes",
    )
    situacao_anterior = models.CharField(max_length=20, choices=ImpressoraMonitorada.SITUACAO_CHOICES)
    situacao_nova = models.CharField(max_length=20, choices=ImpressoraMonitorada.SITUACAO_CHOICES)
    setor_anterior = models.ForeignKey(
        Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentacoes_impressora_origem",
    )
    setor_novo = models.ForeignKey(
        Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentacoes_impressora_destino",
    )
    ip_anterior = models.GenericIPAddressField(null=True, blank=True)
    ip_novo = models.GenericIPAddressField(null=True, blank=True)
    local_anterior = models.CharField(max_length=180, blank=True, default="")
    local_novo = models.CharField(max_length=180, blank=True, default="")
    observacao = models.TextField(blank=True, default="")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="movimentacoes_impressoras",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Movimentação de impressora"
        verbose_name_plural = "Movimentações de impressoras"

    def __str__(self):
        return f"{self.impressora} - {self.get_situacao_nova_display()}"


class LeituraImpressora(models.Model):
    impressora = models.ForeignKey(
        ImpressoraMonitorada, on_delete=models.CASCADE, related_name="leituras",
    )
    online = models.BooleanField(default=False)
    status_dispositivo = models.CharField(max_length=255, blank=True, default="")
    toner_percentual = models.PositiveSmallIntegerField(null=True, blank=True)
    cilindro_percentual = models.PositiveSmallIntegerField(null=True, blank=True)
    erro = models.TextField(blank=True, default="")
    coletado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-coletado_em"]
        verbose_name = "Leitura de impressora"
        verbose_name_plural = "Leituras de impressoras"
        indexes = [models.Index(fields=["impressora", "-coletado_em"])]

    def __str__(self):
        return f"{self.impressora} - {self.coletado_em:%d/%m/%Y %H:%M}"


class MonitoramentoActiveDirectory(models.Model):
    controlador = models.CharField(max_length=255, unique=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    online = models.BooleanField(default=False)
    ldap_ok = models.BooleanField(default=False)
    kerberos_ok = models.BooleanField(default=False)
    dns_ok = models.BooleanField(default=False)
    smb_ok = models.BooleanField(default=False)
    latencia_ms = models.PositiveIntegerField(null=True, blank=True)
    detalhe = models.TextField(blank=True, default="")
    ultima_consulta = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Monitoramento do Active Directory"
        verbose_name_plural = "Monitoramentos do Active Directory"
        ordering = ["controlador"]

    def __str__(self):
        return self.controlador

    @property
    def possui_alerta(self):
        return not all((self.online, self.ldap_ok, self.kerberos_ok, self.dns_ok, self.smb_ok))


class MonitoramentoServidor(models.Model):
    hostname = models.CharField(max_length=255, unique=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    cpu_percentual = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    memoria_percentual = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    memoria_total_gb = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    disco_percentual = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    disco_livre_gb = models.DecimalField(max_digits=12, decimal_places=1, null=True, blank=True)
    uptime_segundos = models.PositiveBigIntegerField(default=0)
    detalhe = models.TextField(blank=True, default="")
    ultima_consulta = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Monitoramento do servidor"
        verbose_name_plural = "Monitoramentos dos servidores"
        ordering = ["hostname"]

    def __str__(self):
        return self.hostname

    @property
    def possui_alerta(self):
        return any(
            valor is not None and float(valor) >= limite
            for valor, limite in (
                (self.cpu_percentual, 90),
                (self.memoria_percentual, 90),
                (self.disco_percentual, 85),
            )
        )


class MonitoramentoRede(models.Model):
    nome = models.CharField(max_length=120, unique=True, default="Rede HSFOS")
    gateway_ip = models.GenericIPAddressField(default="192.168.0.1")
    gateway_ok = models.BooleanField(default=False)
    dns_ip = models.GenericIPAddressField(default="192.168.0.30")
    dns_ok = models.BooleanField(default=False)
    switch_ip = models.GenericIPAddressField(default="192.168.0.53")
    switch_ok = models.BooleanField(default=False)
    switch_modelo = models.CharField(max_length=255, blank=True, default="")
    switch_uptime_segundos = models.PositiveBigIntegerField(default=0)
    switch_interfaces = models.PositiveIntegerField(default=0)
    detalhe = models.TextField(blank=True, default="")
    ultima_consulta = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Monitoramento de rede"
        verbose_name_plural = "Monitoramentos de rede"

    def __str__(self):
        return self.nome

    @property
    def possui_alerta(self):
        return not all((self.gateway_ok, self.dns_ok, self.switch_ok))
