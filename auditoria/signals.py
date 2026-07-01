from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from avisos.models import AvisoComunicado
from documentos.models import DocumentoProtocolo
from .models import RegistroAuditoria


def obter_ip_request(request):
    if not request:
        return None

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


@receiver(post_save, sender=AvisoComunicado)
def registrar_auditoria_aviso(sender, instance, created, **kwargs):
    usuario = instance.criado_por if instance.criado_por else None
    unidade = instance.unidade if instance.unidade else None

    acao = 'criado' if created else 'alterado'
    acao_texto = 'criado' if created else 'alterado'

    RegistroAuditoria.objects.create(
        modulo='avisos',
        acao=acao,
        titulo=f'Aviso {acao_texto}: {instance.titulo}',
        descricao=(
            f'Tipo: {instance.get_tipo_display()}\n'
            f'Prioridade: {instance.get_prioridade_display()}\n'
            f'Ativo: {"Sim" if instance.ativo else "Não"}\n'
            f'Exibir no dashboard: {"Sim" if instance.exibir_no_dashboard else "Não"}'
        ),
        modelo='AvisoComunicado',
        objeto_id=str(instance.id),
        usuario=usuario,
        unidade=unidade,
    )


@receiver(post_save, sender=DocumentoProtocolo)
def registrar_auditoria_documento(sender, instance, created, **kwargs):
    usuario = instance.criado_por if instance.criado_por else None
    unidade = instance.unidade if instance.unidade else None

    acao = 'criado' if created else 'alterado'
    acao_texto = 'criado' if created else 'alterado'

    codigo = f'{instance.codigo} - ' if instance.codigo else ''

    RegistroAuditoria.objects.create(
        modulo='documentos',
        acao=acao,
        titulo=f'Documento {acao_texto}: {codigo}{instance.titulo}',
        descricao=(
            f'Tipo: {instance.get_tipo_display()}\n'
            f'Categoria: {instance.get_categoria_display()}\n'
            f'Status: {instance.get_status_display()}\n'
            f'Versão: {instance.versao or "Não informada"}\n'
            f'Ativo: {"Sim" if instance.ativo else "Não"}'
        ),
        modelo='DocumentoProtocolo',
        objeto_id=str(instance.id),
        usuario=usuario,
        unidade=unidade,
    )


@receiver(user_logged_in)
def registrar_login_usuario(sender, request, user, **kwargs):
    unidade = user.unidade if hasattr(user, 'unidade') and user.unidade else None
    ip_origem = obter_ip_request(request)

    RegistroAuditoria.objects.create(
        modulo='usuarios',
        acao='login',
        titulo=f'Login realizado: {user.get_full_name() or user.username}',
        descricao=(
            f'Usuário: {user.username}\n'
            f'Nome: {user.get_full_name() or "Não informado"}\n'
            f'E-mail: {user.email or "Não informado"}\n'
            f'Unidade: {unidade.nome if unidade else "Não informada"}\n'
            f'IP de origem: {ip_origem or "Não identificado"}'
        ),
        modelo='Usuario',
        objeto_id=str(user.id),
        usuario=user,
        unidade=unidade,
        ip_origem=ip_origem,
    )


@receiver(user_logged_out)
def registrar_logout_usuario(sender, request, user, **kwargs):
    if not user or not user.is_authenticated:
        return

    unidade = user.unidade if hasattr(user, 'unidade') and user.unidade else None
    ip_origem = obter_ip_request(request)

    RegistroAuditoria.objects.create(
        modulo='usuarios',
        acao='logout',
        titulo=f'Logout realizado: {user.get_full_name() or user.username}',
        descricao=(
            f'Usuário: {user.username}\n'
            f'Nome: {user.get_full_name() or "Não informado"}\n'
            f'E-mail: {user.email or "Não informado"}\n'
            f'Unidade: {unidade.nome if unidade else "Não informada"}\n'
            f'IP de origem: {ip_origem or "Não identificado"}'
        ),
        modelo='Usuario',
        objeto_id=str(user.id),
        usuario=user,
        unidade=unidade,
        ip_origem=ip_origem,
    )