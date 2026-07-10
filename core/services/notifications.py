from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import NotificacaoUsuario


def criar_notificacao_usuario(
    *, usuario, titulo, origem, objeto_id='', descricao='', tipo='info',
    icone='🔔', link=''
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
                },
            )
    except IntegrityError:
        notificacao = NotificacaoUsuario.objects.get(
            usuario=usuario,
            origem=origem,
            objeto_id=str(objeto_id or ''),
        )
        criada = False
    return notificacao, criada


def listar_notificacoes(usuario, limite=15, somente_nao_lidas=False):
    notificacoes = NotificacaoUsuario.objects.filter(usuario=usuario)
    if somente_nao_lidas:
        notificacoes = notificacoes.filter(lida=False)
    return notificacoes[:limite]


def contar_nao_lidas(usuario):
    return NotificacaoUsuario.objects.filter(usuario=usuario, lida=False).count()


def marcar_como_lida(usuario, notificacao_id):
    notificacao = NotificacaoUsuario.objects.get(
        id=notificacao_id,
        usuario=usuario,
    )
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.lida_em = timezone.now()
        notificacao.save(update_fields=['lida', 'lida_em'])
    return notificacao


def marcar_todas_como_lidas(usuario):
    return NotificacaoUsuario.objects.filter(
        usuario=usuario,
        lida=False,
    ).update(lida=True, lida_em=timezone.now())
