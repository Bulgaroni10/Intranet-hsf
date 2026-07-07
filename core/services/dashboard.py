def kpi_card(titulo, valor, subtitulo="", icone="📊", tipo="default"):
    return {
        "titulo": titulo,
        "valor": valor,
        "subtitulo": subtitulo,
        "icone": icone,
        "tipo": tipo,
    }


def breadcrumb(*itens):
    return list(itens)