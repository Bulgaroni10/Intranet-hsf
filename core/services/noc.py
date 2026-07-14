from django.utils import timezone

from inventario_ti.models import ComputadorInventario, ErroAgenteInventario, ImpressoraMonitorada, MonitoramentoActiveDirectory, MonitoramentoServidor, MonitoramentoRede, SuprimentoTI
from status_sistemas.models import OcorrenciaSistema, SistemaMonitorado


def montar_contexto_noc(user):
    unidade = getattr(user, 'unidade', None)
    computadores = ComputadorInventario.objects.select_related('unidade').order_by('hostname')
    erros = ErroAgenteInventario.objects.select_related('unidade').order_by('-criado_em')
    ocorrencias = OcorrenciaSistema.objects.filter(ativo=True).select_related('sistema', 'unidade')
    impressoras = ImpressoraMonitorada.objects.filter(ativo=True).select_related('unidade')
    active_directory = MonitoramentoActiveDirectory.objects.order_by('controlador').first()
    servidores = MonitoramentoServidor.objects.order_by('hostname')
    rede = MonitoramentoRede.objects.first()
    suprimentos_baixos = SuprimentoTI.objects.filter(ativo=True, quantidade__lte=5).select_related('unidade')
    computadores = computadores.filter(unidade=unidade)
    erros = erros.filter(unidade=unidade)
    ocorrencias = ocorrencias.filter(unidade=unidade) | ocorrencias.filter(unidade__isnull=True)
    impressoras = impressoras.filter(unidade=unidade)
    suprimentos_baixos = suprimentos_baixos.filter(unidade=unidade)

    # Estes monitores representam a infraestrutura local de Osasco. Outras
    # unidades terão seus próprios registros quando os coletores forem ativados.
    if not unidade or unidade.sigla.upper() != 'HSFOS':
        active_directory = None
        servidores = MonitoramentoServidor.objects.none()
        rede = None

    computadores = list(computadores)
    online = [item for item in computadores if item.online]
    offline = [item for item in computadores if not item.online]
    ocorrencias = list(ocorrencias.order_by('-impacto', '-atualizado_em'))
    sistemas = SistemaMonitorado.objects.filter(ativo=True).order_by('ordem', 'nome')
    incidentes_por_sistema = {item.sistema_id: item for item in ocorrencias}
    status_sistemas = [{
        'sistema': sistema,
        'ocorrencia': incidentes_por_sistema.get(sistema.id),
    } for sistema in sistemas]
    impressoras = list(impressoras.order_by('-online', 'local'))
    impressoras_alerta = [item for item in impressoras if item.possui_alerta]
    servidores = list(servidores)
    servidores_alerta = [item for item in servidores if item.possui_alerta]
    suprimentos_baixos = list(suprimentos_baixos.order_by('quantidade', 'nome'))

    return {
        'agora': timezone.localtime(), 'computadores': computadores,
        'computadores_online': online, 'computadores_offline': offline,
        'total_computadores': len(computadores), 'total_online': len(online),
        'total_offline': len(offline), 'status_sistemas': status_sistemas,
        'ocorrencias': ocorrencias, 'erros_recentes': erros[:8],
        'impressoras': impressoras,
        'total_impressoras': len(impressoras),
        'impressoras_online': sum(1 for item in impressoras if item.online),
        'alertas_impressoras': len(impressoras_alerta),
        'impressoras_alerta': impressoras_alerta,
        'active_directory': active_directory,
        'servidores': servidores,
        'rede': rede,
        'suprimentos_baixos': suprimentos_baixos,
        'total_suprimentos_baixos': len(suprimentos_baixos),
        'total_alertas_ativos': (
            len(impressoras_alerta) + len(suprimentos_baixos)
            + len(ocorrencias) + len(servidores_alerta)
        ),
    }
