import os
from uuid import uuid4


def caminho_upload(instance, filename):
    """
    Gera caminho seguro para uploads.

    Exemplo:
    uploads/solicitacoes/arquivo-uuid.pdf
    """

    nome, extensao = os.path.splitext(filename)
    novo_nome = f"{uuid4().hex}{extensao.lower()}"

    app_name = instance.__class__.__module__.split(".")[0]

    return f"uploads/{app_name}/{novo_nome}"