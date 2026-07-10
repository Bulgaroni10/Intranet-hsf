from django.db.models import Q

from avisos.views import buscar_avisos_visiveis
from base_conhecimento.views import buscar_documentos_visiveis as buscar_conhecimento_visivel
from documentos.views import buscar_documentos_visiveis
from modulos.models import Modulo
from ramais_contatos.views import buscar_contatos_visiveis
from solicitacoes_ti.models import SolicitacaoTI

from core.services.dashboard import filtrar_chamados_ti_dashboard
from core.services.permissions import usuario_eh_admin_ti


LIMITE_POR_FONTE = 8


def _item(tipo, titulo, descricao, url, icone):
    return {'tipo': tipo, 'titulo': titulo, 'descricao': descricao, 'url': url, 'icone': icone}


def buscar_global(request, termo):
    termo = (termo or '').strip()
    if len(termo) < 2:
        return []
    user = request.user
    resultados = []

    modulos = Modulo.objects.filter(ativo=True).filter(
        Q(nome__icontains=termo) | Q(descricao__icontains=termo) | Q(palavras_chave__icontains=termo)
    )
    if not usuario_eh_admin_ti(user):
        modulos = modulos.filter(Q(grupos_permitidos__in=user.groups.all()) | Q(grupos_permitidos__isnull=True)).distinct()
    resultados += [_item('Módulo', x.nome, x.descricao, x.link, x.icone) for x in modulos[:LIMITE_POR_FONTE]]

    documentos = buscar_documentos_visiveis(user).filter(
        Q(codigo__icontains=termo) | Q(titulo__icontains=termo) | Q(descricao__icontains=termo)
    )[:LIMITE_POR_FONTE]
    resultados += [_item('Documento', x.titulo, x.codigo or x.get_tipo_display(), '/portal/modulos/documentos/', '📄') for x in documentos]

    conhecimento = buscar_conhecimento_visivel(request).filter(
        Q(titulo__icontains=termo) | Q(descricao__icontains=termo) | Q(categoria__nome__icontains=termo)
    )[:LIMITE_POR_FONTE]
    resultados += [_item('Conhecimento', x.titulo, x.descricao[:140], '/portal/modulos/base-conhecimento/', '📚') for x in conhecimento]

    contatos = buscar_contatos_visiveis(request).filter(
        Q(nome__icontains=termo) | Q(setor__icontains=termo) | Q(ramal__icontains=termo) | Q(email__icontains=termo)
    )[:LIMITE_POR_FONTE]
    resultados += [_item('Ramal', x.nome, f'{x.setor} • Ramal {x.ramal}'.strip(' •'), '/portal/modulos/ramais-contatos/', '☎') for x in contatos]

    avisos = buscar_avisos_visiveis(user).filter(Q(titulo__icontains=termo) | Q(resumo__icontains=termo) | Q(mensagem__icontains=termo))[:LIMITE_POR_FONTE]
    resultados += [_item('Aviso', x.titulo, x.resumo or x.mensagem[:140], '/portal/modulos/avisos/', '📢') for x in avisos]

    chamados = filtrar_chamados_ti_dashboard(user, SolicitacaoTI.objects.filter(ativo=True)).filter(
        Q(titulo__icontains=termo) | Q(descricao__icontains=termo)
    )[:LIMITE_POR_FONTE]
    resultados += [_item('Solicitação TI', f'#{x.id} — {x.titulo}', x.get_status_display(), f'/portal/modulos/solicitacoes-ti/detalhe/{x.id}/', '🎫') for x in chamados]
    return resultados
