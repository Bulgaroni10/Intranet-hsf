from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from modulos.models import Modulo
from usuarios.models import Unidade
from .models import RegistroAuditoria


NOME_MODULO_AUDITORIA = 'Auditoria / Histórico'


def usuario_pode_acessar_modulo(user, nome_modulo):
    if user.is_superuser or user.groups.filter(name='TI Administrador').exists():
        return True

    try:
        modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    except Modulo.DoesNotExist:
        return False

    if not modulo.grupos_permitidos.exists():
        return True

    return modulo.grupos_permitidos.filter(
        id__in=user.groups.values_list('id', flat=True)
    ).exists()


def usuario_pode_ver_auditoria(user):
    if user.is_superuser:
        return True

    if user.groups.filter(name='TI Administrador').exists():
        return True

    if user.groups.filter(name='Auditoria Interna').exists():
        return True

    return False


@login_required(login_url='/')
def auditoria_registros(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_AUDITORIA):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_ver_auditoria(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    registros = RegistroAuditoria.objects.select_related(
        'usuario',
        'unidade'
    ).all()

    busca = request.GET.get('busca', '').strip()
    modulo = request.GET.get('modulo', '').strip()
    acao = request.GET.get('acao', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    usuario_id = request.GET.get('usuario', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    if busca:
        registros = registros.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(modelo__icontains=busca) |
            Q(objeto_id__icontains=busca) |
            Q(ip_origem__icontains=busca) |
            Q(usuario__username__icontains=busca) |
            Q(usuario__first_name__icontains=busca) |
            Q(usuario__last_name__icontains=busca) |
            Q(usuario__email__icontains=busca) |
            Q(unidade__nome__icontains=busca) |
            Q(unidade__sigla__icontains=busca)
        )

    if modulo:
        registros = registros.filter(modulo=modulo)

    if acao:
        registros = registros.filter(acao=acao)

    if unidade_id:
        if unidade_id == 'geral':
            registros = registros.filter(unidade__isnull=True)
        else:
            registros = registros.filter(unidade_id=unidade_id)

    if usuario_id:
        if usuario_id == 'sistema':
            registros = registros.filter(usuario__isnull=True)
        else:
            registros = registros.filter(usuario_id=usuario_id)

    if data_inicio:
        registros = registros.filter(criado_em__date__gte=data_inicio)

    if data_fim:
        registros = registros.filter(criado_em__date__lte=data_fim)

    total_registros = registros.count()
    total_criados = registros.filter(acao='criado').count()
    total_alterados = registros.filter(acao='alterado').count()
    total_encerrados = registros.filter(acao='encerrado').count()
    total_login = registros.filter(acao='login').count()

    registros = registros.order_by('-criado_em')[:300]

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    Usuario = get_user_model()

    usuarios = Usuario.objects.filter(
        registros_auditoria__isnull=False
    ).distinct().order_by(
        'first_name',
        'last_name',
        'username'
    )

    return render(request, 'auditoria/auditoria_registros.html', {
        'registros': registros,
        'unidades': unidades,
        'usuarios': usuarios,
        'modulos': RegistroAuditoria.MODULO_CHOICES,
        'acoes': RegistroAuditoria.ACAO_CHOICES,
        'busca': busca,
        'modulo': modulo,
        'acao': acao,
        'unidade_id': unidade_id,
        'usuario_id': usuario_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_registros': total_registros,
        'total_criados': total_criados,
        'total_alterados': total_alterados,
        'total_encerrados': total_encerrados,
        'total_login': total_login,
    })