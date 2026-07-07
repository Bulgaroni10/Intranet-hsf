from django import template

register = template.Library()


@register.filter
def status_badge(status):
    mapa = {
        "aberta": "gsf-badge-info",
        "em_andamento": "gsf-badge-warning",
        "aguardando": "gsf-badge-warning",
        "concluida": "gsf-badge-success",
        "cancelada": "gsf-badge-danger",
        "critica": "gsf-badge-danger",
        "alta": "gsf-badge-warning",
        "media": "gsf-badge-info",
        "baixa": "gsf-badge-success",
    }

    return mapa.get(status, "gsf-badge")


@register.filter
def default_dash(value):
    if value is None or value == "":
        return "-"

    return value