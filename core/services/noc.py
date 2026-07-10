from django.utils import timezone

from inventario_ti.models import ComputadorInventario, ErroAgenteInventario
from status_sistemas.models import OcorrenciaSistema, SistemaMonitorado


def montar_contexto_noc(user):
    computadores = ComputadorInventario.objects.select_related('unidade').order_by('hostname')
    erros = ErroAgenteInventario.objects.select_related('unidade').order_by('-criado_em')
    ocorrencias = OcorrenciaSistema.objects.filter(ativo=True).select_related('sistema', 'unidade')
    if not user.is_superuser:
        computadores = computadores.filter(unidade=user.unidade)
        erros = erros.filter(unidade=user.unidade)
        ocorrencias = ocorrencias.filter(unidade=user.unidade) | ocorrencias.filter(unidade__isnull=True)

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

    return {
        'agora': timezone.localtime(), 'computadores': computadores,
        'computadores_online': online, 'computadores_offline': offline,
        'total_computadores': len(computadores), 'total_online': len(online),
        'total_offline': len(offline), 'status_sistemas': status_sistemas,
        'ocorrencias': ocorrencias, 'erros_recentes': erros[:8],
    }
