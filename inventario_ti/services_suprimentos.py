from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import NotificacaoUsuario
from core.services.permissions import PERFIS_TI


LIMITE_ALERTA_SUPRIMENTO = 5


def sincronizar_alerta_suprimento(item):
    origem = "suprimento_estoque_baixo"
    objeto_id = str(item.pk)
    notificacoes = NotificacaoUsuario.objects.filter(origem=origem, objeto_id=objeto_id, lida=False)

    if not item.ativo or item.quantidade > LIMITE_ALERTA_SUPRIMENTO:
        notificacoes.update(lida=True, lida_em=timezone.now())
        return

    usuarios = get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=PERFIS_TI)
    ).distinct()
    if item.unidade_id:
        usuarios = usuarios.filter(unidade_id=item.unidade_id)

    titulo = f"Estoque baixo: {item.nome}"
    descricao = f"Restam {item.quantidade} unidade(s). Limite de alerta: {LIMITE_ALERTA_SUPRIMENTO}."
    for usuario in usuarios:
        notificacao, _criada = NotificacaoUsuario.objects.get_or_create(
            usuario=usuario,
            origem=origem,
            objeto_id=objeto_id,
            defaults={
                "titulo": titulo,
                "descricao": descricao,
                "tipo": "warning" if item.quantidade else "danger",
                "icone": "📦",
                "link": f"/portal/modulos/inventario-ti/suprimentos/{item.id}/",
            },
        )
        campos = []
        for campo, valor in {
            "titulo": titulo,
            "descricao": descricao,
            "tipo": "warning" if item.quantidade else "danger",
            "lida": False,
            "lida_em": None,
        }.items():
            if getattr(notificacao, campo) != valor:
                setattr(notificacao, campo, valor)
                campos.append(campo)
        if campos:
            notificacao.save(update_fields=campos)
