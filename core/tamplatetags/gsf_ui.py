from django import template


register = template.Library()


@register.inclusion_tag(
    "components/ui/hero.html",
    takes_context=True,
)
def gsf_hero(
    context,
    titulo,
    subtitulo="",
    eyebrow="",
    icone="",
    acao_texto="",
    acao_url="",
    acao_classe="gsf-btn-primary",
    acao_secundaria_texto="",
    acao_secundaria_url="",
):
    return {
        "request": context.get("request"),
        "titulo": titulo,
        "subtitulo": subtitulo,
        "eyebrow": eyebrow,
        "icone": icone,
        "acao_texto": acao_texto,
        "acao_url": acao_url,
        "acao_classe": acao_classe,
        "acao_secundaria_texto": acao_secundaria_texto,
        "acao_secundaria_url": acao_secundaria_url,
    }