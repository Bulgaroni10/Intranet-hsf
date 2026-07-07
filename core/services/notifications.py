def notificar_usuario(usuario, titulo, mensagem, tipo="info", link=""):
    """
    Serviço base de notificações.

    Futuramente poderá enviar:
    - alerta na intranet
    - e-mail
    - Teams
    - WhatsApp
    """

    return {
        "usuario": usuario,
        "titulo": titulo,
        "mensagem": mensagem,
        "tipo": tipo,
        "link": link,
    }


def sucesso(usuario, mensagem, link=""):
    return notificar_usuario(
        usuario=usuario,
        titulo="Sucesso",
        mensagem=mensagem,
        tipo="success",
        link=link,
    )


def alerta(usuario, mensagem, link=""):
    return notificar_usuario(
        usuario=usuario,
        titulo="Atenção",
        mensagem=mensagem,
        tipo="warning",
        link=link,
    )


def erro(usuario, mensagem, link=""):
    return notificar_usuario(
        usuario=usuario,
        titulo="Erro",
        mensagem=mensagem,
        tipo="danger",
        link=link,
    )