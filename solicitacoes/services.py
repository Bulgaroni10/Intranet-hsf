from .models import HistoricoSolicitacao


def nome_usuario(usuario):
    if not usuario:
        return 'Sistema'

    return usuario.get_full_name() or usuario.username


def registrar_historico(
    solicitacao,
    usuario,
    tipo,
    titulo,
    descricao='',
    valor_anterior='',
    valor_novo='',
):
    return HistoricoSolicitacao.objects.create(
        solicitacao=solicitacao,
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
        tipo=tipo,
        titulo=titulo,
        descricao=descricao,
        valor_anterior=valor_anterior or '',
        valor_novo=valor_novo or '',
    )


def rotulo_choice(choices, valor):
    mapa = dict(choices)
    return mapa.get(valor, valor or 'Não informado')