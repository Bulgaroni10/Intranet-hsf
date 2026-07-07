from django.utils import timezone


def registrar_evento(
    tipo,
    descricao,
    usuario=None,
    objeto=None,
    metadata=None,
):
    """
    Serviço central para registrar eventos do sistema.

    Nesta primeira versão, ele apenas retorna um dicionário.
    Depois vamos ligar isso em banco, notificações e auditoria.
    """

    return {
        "tipo": tipo,
        "descricao": descricao,
        "usuario": usuario,
        "objeto": objeto,
        "metadata": metadata or {},
        "criado_em": timezone.now(),
    }