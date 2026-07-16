from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from core.models import NotificacaoUsuario


def criar_notificacao_usuario(
    *, usuario, titulo, origem, objeto_id='', descricao='', tipo='info',
    icone='🔔', link='', unidade=None
):
    """Cria uma notificação idempotente para um usuário específico."""
    try:
        with transaction.atomic():
            notificacao, criada = NotificacaoUsuario.objects.get_or_create(
                usuario=usuario,
                origem=origem,
                objeto_id=str(objeto_id or ''),
                defaults={
                    'titulo': titulo,
                    'descricao': descricao,
                    'tipo': tipo,
                    'icone': icone,
                    'link': link,
                    'unidade': unidade,
                },
            )
    except IntegrityError:
        notificacao = NotificacaoUsuario.objects.get(
            usuario=usuario,
            origem=origem,
            objeto_id=str(objeto_id or ''),
        )
        criada = False
    if not criada:
        valores = {
            'titulo': titulo,
            'descricao': descricao,
            'tipo': tipo,
            'icone': icone,
            'link': link,
        }
        if unidade is not None:
            valores['unidade'] = unidade
        campos = []
        for campo, valor in valores.items():
            atual = notificacao.unidade_id if campo == 'unidade' else getattr(notificacao, campo)
            esperado = valor.id if campo == 'unidade' else valor
            if atual != esperado:
                setattr(notificacao, campo, valor)
                campos.append(campo)
        if campos:
            notificacao.lida = False
            notificacao.lida_em = None
            campos.extend(['lida', 'lida_em', 'atualizado_em'])
            notificacao.save(update_fields=campos)
    return notificacao, criada


def listar_notificacoes(usuario, limite=15, somente_nao_lidas=False, unidade=None):
    notificacoes = NotificacaoUsuario.objects.filter(usuario=usuario)
    if unidade is not None:
        notificacoes = notificacoes.filter(Q(unidade=unidade) | Q(unidade__isnull=True))
    if somente_nao_lidas:
        notificacoes = notificacoes.filter(lida=False)
    return notificacoes[:limite]


def contar_nao_lidas(usuario, unidade=None):
    notificacoes = NotificacaoUsuario.objects.filter(usuario=usuario, lida=False)
    if unidade is not None:
        notificacoes = notificacoes.filter(Q(unidade=unidade) | Q(unidade__isnull=True))
    return notificacoes.count()


def marcar_como_lida(usuario, notificacao_id, unidade=None):
    notificacoes = NotificacaoUsuario.objects.filter(
        id=notificacao_id,
        usuario=usuario,
    )
    if unidade is not None:
        notificacoes = notificacoes.filter(Q(unidade=unidade) | Q(unidade__isnull=True))
    notificacao = notificacoes.get()
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.lida_em = timezone.now()
        notificacao.save(update_fields=['lida', 'lida_em'])
    return notificacao


def marcar_todas_como_lidas(usuario, unidade=None):
    notificacoes = NotificacaoUsuario.objects.filter(
        usuario=usuario,
        lida=False,
    )
    if unidade is not None:
        notificacoes = notificacoes.filter(Q(unidade=unidade) | Q(unidade__isnull=True))
    return notificacoes.update(lida=True, lida_em=timezone.now())
