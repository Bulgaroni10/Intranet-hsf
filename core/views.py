import csv
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models import Q, Prefetch
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from modulos.models import Modulo
from conteudos.models import ConteudoModulo
from usuarios.models import Unidade
from convenios.models import (
    Convenio,
    PlanoConvenio,
    Especialidade,
    RegraAtendimentoConvenio,
    ProcedimentoProibidoPlano,
)
from status_sistemas.models import SistemaMonitorado, OcorrenciaSistema
from avisos.models import AvisoComunicado
from documentos.models import DocumentoProtocolo
from auditoria.models import RegistroAuditoria
from solicitacoes_ti.models import SolicitacaoTI


def usuario_pode_acessar_modulo(user, nome_modulo):
    if user.is_superuser or user.groups.filter(name='TI Administrador').exists():
        return True

    try:
        modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    except Modulo.DoesNotExist:
        return False

    if not modulo.grupos_permitidos.exists():
        return True

    return modulo.grupos_permitidos.filter(
        id__in=user.groups.values_list('id', flat=True)
    ).exists()


def usuario_pode_acessar_link_modulo(user, link_modulo):
    if user.is_superuser or user.groups.filter(name='TI Administrador').exists():
        return True

    try:
        modulo = Modulo.objects.get(link=link_modulo, ativo=True)
    except Modulo.DoesNotExist:
        return False

    if not modulo.grupos_permitidos.exists():
        return True

    return modulo.grupos_permitidos.filter(
        id__in=user.groups.values_list('id', flat=True)
    ).exists()


def usuario_pode_acessar_administracao(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def usuario_eh_admin_ti(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def usuario_pode_gerenciar_status(user):
    return usuario_eh_admin_ti(user)


def usuario_pode_gerenciar_links_uteis(user):
    return usuario_eh_admin_ti(user)


def usuario_pode_gerenciar_manuais(user):
    return usuario_eh_admin_ti(user)


def usuario_pode_gerenciar_mv(user):
    return usuario_eh_admin_ti(user)


def obter_unidade_usuario(user):
    return getattr(user, 'unidade', None)


def obter_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def montar_acessos_botoes_rapidos(user):
    return {
        'avisos': usuario_pode_acessar_link_modulo(user, '/portal/modulos/avisos/'),
        'documentos': usuario_pode_acessar_link_modulo(user, '/portal/modulos/documentos/'),
        'status_sistemas': usuario_pode_acessar_link_modulo(user, '/portal/modulos/status-sistemas/'),
        'links_uteis': usuario_pode_acessar_link_modulo(user, '/portal/modulos/links-uteis/'),
        'manuais': usuario_pode_acessar_link_modulo(user, '/portal/modulos/manuais-procedimentos/'),
        'ramais': usuario_pode_acessar_link_modulo(user, '/portal/modulos/ramais-contatos/'),
    }


def buscar_conteudos_permitidos(user, modulo):
    unidade_usuario = obter_unidade_usuario(user)

    conteudos = ConteudoModulo.objects.filter(
        modulo=modulo,
        ativo=True
    ).filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True)
    )

    if usuario_eh_admin_ti(user):
        return conteudos.order_by('tipo', 'ordem', 'titulo')

    grupos_usuario = user.groups.all()

    return conteudos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().order_by('tipo', 'ordem', 'titulo')


def buscar_avisos_dashboard(user):
    agora = timezone.now()
    unidade_usuario = obter_unidade_usuario(user)

    avisos = AvisoComunicado.objects.filter(
        ativo=True,
        exibir_no_dashboard=True,
        publicado_em__lte=agora,
    ).filter(
        Q(expira_em__isnull=True) |
        Q(expira_em__gte=agora)
    )

    if usuario_eh_admin_ti(user):
        return avisos.select_related(
            'unidade',
            'criado_por'
        ).prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ).order_by(
            '-fixar_no_topo',
            '-publicado_em',
            'titulo'
        )[:5]

    avisos = avisos.filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=unidade_usuario)
    )

    grupos_usuario = user.groups.all()

    return avisos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().select_related(
        'unidade',
        'criado_por'
    ).prefetch_related(
        'grupos_permitidos',
        'unidades_compartilhadas'
    ).order_by(
        '-fixar_no_topo',
        '-publicado_em',
        'titulo'
    )[:5]


def buscar_documentos_dashboard(user):
    hoje = timezone.localdate()
    limite_30_dias = hoje + timezone.timedelta(days=30)
    unidade_usuario = obter_unidade_usuario(user)
    setor_usuario = getattr(user, 'setor', None)

    documentos = DocumentoProtocolo.objects.filter(
        ativo=True,
        exibir_no_dashboard=True,
    ).exclude(
        status='inativo'
    ).filter(
        Q(status='em_revisao') |
        Q(data_validade__isnull=False, data_validade__lt=hoje) |
        Q(
            data_validade__isnull=False,
            data_validade__gte=hoje,
            data_validade__lte=limite_30_dias
        )
    )

    if usuario_eh_admin_ti(user):
        return documentos.select_related(
            'unidade',
            'setor',
            'criado_por'
        ).prefetch_related(
            'grupos_permitidos',
            'unidades_compartilhadas'
        ).order_by(
            'data_validade',
            'titulo'
        )[:6]

    documentos = documentos.filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True) |
        Q(unidades_compartilhadas=unidade_usuario)
    ).filter(
        Q(setor=setor_usuario) |
        Q(setor__isnull=True)
    )

    grupos_usuario = user.groups.all()

    return documentos.filter(
        Q(grupos_permitidos__in=grupos_usuario) |
        Q(grupos_permitidos__isnull=True)
    ).distinct().select_related(
        'unidade',
        'setor',
        'criado_por'
    ).prefetch_related(
        'grupos_permitidos',
        'unidades_compartilhadas'
    ).order_by(
        'data_validade',
        'titulo'
    )[:6]


def registrar_auditoria_generica(request, modulo, acao, titulo, descricao, modelo, objeto_id, unidade=None):
    RegistroAuditoria.objects.create(
        modulo=modulo,
        acao=acao,
        titulo=titulo,
        descricao=descricao,
        modelo=modelo,
        objeto_id=str(objeto_id),
        usuario=request.user,
        unidade=unidade if unidade else obter_unidade_usuario(request.user),
        ip_origem=obter_ip_cliente(request),
    )


def registrar_auditoria_sistema(request, sistema, acao, titulo):
    registrar_auditoria_generica(
        request=request,
        modulo='status_sistemas',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Sistema: {sistema.nome}\n'
            f'Descrição: {sistema.descricao or "Não informada"}\n'
            f'Categoria: {sistema.get_categoria_display()}\n'
            f'Ícone: {sistema.icone}\n'
            f'Ordem: {sistema.ordem}\n'
            f'Ativo: {"Sim" if sistema.ativo else "Não"}'
        ),
        modelo='SistemaMonitorado',
        objeto_id=sistema.id,
    )


def registrar_auditoria_status_abertura(request, ocorrencia):
    registrar_auditoria_generica(
        request=request,
        modulo='status_sistemas',
        acao='criado',
        titulo=f'Ocorrência aberta: {ocorrencia.titulo}',
        descricao=(
            f'Sistema: {ocorrencia.sistema.nome}\n'
            f'Status: {ocorrencia.get_status_display()}\n'
            f'Impacto: {ocorrencia.get_impacto_display()}\n'
            f'Unidade: {ocorrencia.unidade.nome if ocorrencia.unidade else "Geral / Todas as unidades"}\n'
            f'Previsão: {ocorrencia.previsao or "Não informada"}\n'
            f'Mensagem: {ocorrencia.mensagem or "Não informada"}\n'
            f'Ação da TI: {ocorrencia.acao_ti or "Não informada"}'
        ),
        modelo='OcorrenciaSistema',
        objeto_id=ocorrencia.id,
        unidade=ocorrencia.unidade,
    )


def registrar_auditoria_status_encerramento(request, ocorrencia):
    registrar_auditoria_generica(
        request=request,
        modulo='status_sistemas',
        acao='encerrado',
        titulo=f'Ocorrência encerrada: {ocorrencia.titulo}',
        descricao=(
            f'Sistema: {ocorrencia.sistema.nome}\n'
            f'Status anterior: {ocorrencia.get_status_display()}\n'
            f'Impacto: {ocorrencia.get_impacto_display()}\n'
            f'Unidade: {ocorrencia.unidade.nome if ocorrencia.unidade else "Geral / Todas as unidades"}\n'
            f'Causa raiz: {ocorrencia.causa_raiz or "Não informada"}\n'
            f'Solução aplicada: {ocorrencia.solucao_aplicada or "Não informada"}\n'
            f'Observação final: {ocorrencia.observacao_encerramento or "Não informada"}'
        ),
        modelo='OcorrenciaSistema',
        objeto_id=ocorrencia.id,
        unidade=ocorrencia.unidade,
    )


def registrar_auditoria_link_util(request, link, acao, titulo):
    registrar_auditoria_generica(
        request=request,
        modulo='conteudos',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Link: {link.titulo}\n'
            f'Descrição: {link.descricao or "Não informada"}\n'
            f'URL: {link.link_externo or "Não informada"}\n'
            f'Unidade: {link.unidade.nome if link.unidade else "Geral / Todas as unidades"}\n'
            f'Ordem: {link.ordem}\n'
            f'Ativo: {"Sim" if link.ativo else "Não"}'
        ),
        modelo='ConteudoModulo',
        objeto_id=link.id,
        unidade=link.unidade,
    )


def registrar_auditoria_manual(request, conteudo, acao, titulo):
    grupos = ', '.join(conteudo.grupos_permitidos.values_list('name', flat=True))

    registrar_auditoria_generica(
        request=request,
        modulo='conteudos',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Conteúdo: {conteudo.titulo}\n'
            f'Tipo: {conteudo.get_tipo_display()}\n'
            f'Descrição: {conteudo.descricao or "Não informada"}\n'
            f'Arquivo: {conteudo.arquivo.name if conteudo.arquivo else "Não informado"}\n'
            f'Link externo: {conteudo.link_externo or "Não informado"}\n'
            f'Unidade: {conteudo.unidade.nome if conteudo.unidade else "Geral / Todas as unidades"}\n'
            f'Grupos permitidos: {grupos if grupos else "Todos os usuários com acesso ao módulo"}\n'
            f'Ordem: {conteudo.ordem}\n'
            f'Ativo: {"Sim" if conteudo.ativo else "Não"}'
        ),
        modelo='ConteudoModulo',
        objeto_id=conteudo.id,
        unidade=conteudo.unidade,
    )


def registrar_auditoria_convenio_mv(request, convenio, acao, titulo):
    registrar_auditoria_generica(
        request=request,
        modulo='convenios',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Convênio: {convenio.nome}\n'
            f'Código MV: {convenio.codigo_mv or "Não informado"}\n'
            f'Tipo MV: {convenio.tipo_mv or "Não informado"}\n'
            f'Ativo: {"Sim" if convenio.ativo else "Não"}'
        ),
        modelo='Convenio',
        objeto_id=convenio.id,
    )


def registrar_auditoria_plano_mv(request, plano, acao, titulo):
    registrar_auditoria_generica(
        request=request,
        modulo='convenios',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Convênio: {plano.convenio.nome}\n'
            f'Plano: {plano.nome}\n'
            f'Código MV: {plano.codigo_mv or "Não informado"}\n'
            f'Regra MV: {plano.regra_codigo_mv or "Não informada"} - {plano.regra_nome_mv or "Não informada"}\n'
            f'Índice MV: {plano.indice_codigo_mv or "Não informado"} - {plano.indice_nome_mv or "Não informado"}\n'
            f'Ativo: {"Sim" if plano.ativo else "Não"}'
        ),
        modelo='PlanoConvenio',
        objeto_id=plano.id,
    )


def registrar_auditoria_especialidade_mv(request, especialidade, acao, titulo):
    registrar_auditoria_generica(
        request=request,
        modulo='convenios',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Especialidade: {especialidade.nome}\n'
            f'Ativo: {"Sim" if especialidade.ativo else "Não"}'
        ),
        modelo='Especialidade',
        objeto_id=especialidade.id,
    )


def registrar_auditoria_regra_mv(request, regra, acao, titulo):
    registrar_auditoria_generica(
        request=request,
        modulo='convenios',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Unidade: {regra.unidade.nome}\n'
            f'Convênio: {regra.convenio.nome}\n'
            f'Plano: {regra.plano.nome}\n'
            f'Tipo atendimento: {regra.get_tipo_atendimento_display()}\n'
            f'Especialidade: {regra.especialidade.nome if regra.especialidade else "Geral / Não se aplica"}\n'
            f'Status: {regra.get_status_display()}\n'
            f'Exige autorização: {"Sim" if regra.exige_autorizacao else "Não"}\n'
            f'Observação: {regra.observacao or "Não informada"}\n'
            f'Ativo: {"Sim" if regra.ativo else "Não"}'
        ),
        modelo='RegraAtendimentoConvenio',
        objeto_id=regra.id,
        unidade=regra.unidade,
    )


def registrar_auditoria_procedimento_mv(request, procedimento, acao, titulo):
    registrar_auditoria_generica(
        request=request,
        modulo='convenios',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Convênio: {procedimento.convenio.nome}\n'
            f'Plano: {procedimento.plano.nome}\n'
            f'Código procedimento: {procedimento.codigo_procedimento}\n'
            f'Descrição procedimento: {procedimento.descricao_procedimento}\n'
            f'Ativo: {"Sim" if procedimento.ativo else "Não"}'
        ),
        modelo='ProcedimentoProibidoPlano',
        objeto_id=procedimento.id,
    )


def montar_form_data_sistema(request):
    return {
        'nome': request.POST.get('nome', '').strip(),
        'descricao': request.POST.get('descricao', '').strip(),
        'categoria': request.POST.get('categoria', '').strip(),
        'icone': request.POST.get('icone', '🖥️').strip() or '🖥️',
        'ordem': request.POST.get('ordem', '0').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def sistema_para_form_data(sistema):
    return {
        'nome': sistema.nome,
        'descricao': sistema.descricao,
        'categoria': sistema.categoria,
        'icone': sistema.icone,
        'ordem': sistema.ordem,
        'ativo': sistema.ativo,
    }


def montar_form_data_link_util(request):
    return {
        'unidade': request.POST.get('unidade', '').strip(),
        'titulo': request.POST.get('titulo', '').strip(),
        'descricao': request.POST.get('descricao', '').strip(),
        'link_externo': request.POST.get('link_externo', '').strip(),
        'ordem': request.POST.get('ordem', '0').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def link_util_para_form_data(link):
    return {
        'unidade': str(link.unidade_id) if link.unidade_id else '',
        'titulo': link.titulo,
        'descricao': link.descricao,
        'link_externo': link.link_externo,
        'ordem': link.ordem,
        'ativo': link.ativo,
    }


def montar_form_data_manual(request):
    return {
        'unidade': request.POST.get('unidade', '').strip(),
        'tipo': request.POST.get('tipo', 'manual').strip(),
        'titulo': request.POST.get('titulo', '').strip(),
        'descricao': request.POST.get('descricao', '').strip(),
        'link_externo': request.POST.get('link_externo', '').strip(),
        'ordem': request.POST.get('ordem', '0').strip(),
        'ativo': request.POST.get('ativo') == 'on',
        'remover_arquivo': request.POST.get('remover_arquivo') == 'on',
        'grupos_permitidos': request.POST.getlist('grupos_permitidos'),
    }


def manual_para_form_data(conteudo):
    return {
        'unidade': str(conteudo.unidade_id) if conteudo.unidade_id else '',
        'tipo': conteudo.tipo,
        'titulo': conteudo.titulo,
        'descricao': conteudo.descricao,
        'link_externo': conteudo.link_externo,
        'ordem': conteudo.ordem,
        'ativo': conteudo.ativo,
        'remover_arquivo': False,
        'grupos_permitidos': [str(grupo_id) for grupo_id in conteudo.grupos_permitidos.values_list('id', flat=True)],
    }


def montar_form_data_convenio(request):
    return {
        'codigo_mv': request.POST.get('codigo_mv', '').strip(),
        'nome': request.POST.get('nome', '').strip(),
        'tipo_mv': request.POST.get('tipo_mv', '').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def convenio_para_form_data(convenio):
    return {
        'codigo_mv': convenio.codigo_mv,
        'nome': convenio.nome,
        'tipo_mv': convenio.tipo_mv,
        'ativo': convenio.ativo,
    }


def montar_form_data_plano(request):
    return {
        'convenio': request.POST.get('convenio', '').strip(),
        'codigo_mv': request.POST.get('codigo_mv', '').strip(),
        'nome': request.POST.get('nome', '').strip(),
        'regra_codigo_mv': request.POST.get('regra_codigo_mv', '').strip(),
        'regra_nome_mv': request.POST.get('regra_nome_mv', '').strip(),
        'indice_codigo_mv': request.POST.get('indice_codigo_mv', '').strip(),
        'indice_nome_mv': request.POST.get('indice_nome_mv', '').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def plano_para_form_data(plano):
    return {
        'convenio': str(plano.convenio_id),
        'codigo_mv': plano.codigo_mv,
        'nome': plano.nome,
        'regra_codigo_mv': plano.regra_codigo_mv,
        'regra_nome_mv': plano.regra_nome_mv,
        'indice_codigo_mv': plano.indice_codigo_mv,
        'indice_nome_mv': plano.indice_nome_mv,
        'ativo': plano.ativo,
    }


def montar_form_data_especialidade(request):
    return {
        'nome': request.POST.get('nome', '').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def especialidade_para_form_data(especialidade):
    return {
        'nome': especialidade.nome,
        'ativo': especialidade.ativo,
    }


def montar_form_data_regra(request):
    return {
        'unidade': request.POST.get('unidade', '').strip(),
        'convenio': request.POST.get('convenio', '').strip(),
        'plano': request.POST.get('plano', '').strip(),
        'tipo_atendimento': request.POST.get('tipo_atendimento', '').strip(),
        'especialidade': request.POST.get('especialidade', '').strip(),
        'status': request.POST.get('status', '').strip(),
        'exige_autorizacao': request.POST.get('exige_autorizacao') == 'on',
        'observacao': request.POST.get('observacao', '').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def regra_para_form_data(regra):
    return {
        'unidade': str(regra.unidade_id),
        'convenio': str(regra.convenio_id),
        'plano': str(regra.plano_id),
        'tipo_atendimento': regra.tipo_atendimento,
        'especialidade': str(regra.especialidade_id) if regra.especialidade_id else '',
        'status': regra.status,
        'exige_autorizacao': regra.exige_autorizacao,
        'observacao': regra.observacao,
        'ativo': regra.ativo,
    }


def montar_form_data_procedimento(request):
    return {
        'convenio': request.POST.get('convenio', '').strip(),
        'plano': request.POST.get('plano', '').strip(),
        'codigo_procedimento': request.POST.get('codigo_procedimento', '').strip(),
        'descricao_procedimento': request.POST.get('descricao_procedimento', '').strip(),
        'ativo': request.POST.get('ativo') == 'on',
    }


def procedimento_para_form_data(procedimento):
    return {
        'convenio': str(procedimento.convenio_id),
        'plano': str(procedimento.plano_id),
        'codigo_procedimento': procedimento.codigo_procedimento,
        'descricao_procedimento': procedimento.descricao_procedimento,
        'ativo': procedimento.ativo,
    }


def filtrar_ocorrencias_historico(request, user):
    unidade_usuario = obter_unidade_usuario(user)

    ocorrencias = OcorrenciaSistema.objects.filter(
        ativo=False
    ).select_related(
        'sistema',
        'unidade'
    )

    if not usuario_eh_admin_ti(user):
        ocorrencias = ocorrencias.filter(
            Q(unidade=unidade_usuario) |
            Q(unidade__isnull=True)
        )

    busca = request.GET.get('busca', '').strip()
    sistema_id = request.GET.get('sistema', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    status = request.GET.get('status', '').strip()
    impacto = request.GET.get('impacto', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    if busca:
        ocorrencias = ocorrencias.filter(
            Q(titulo__icontains=busca) |
            Q(mensagem__icontains=busca) |
            Q(previsao__icontains=busca) |
            Q(acao_ti__icontains=busca) |
            Q(causa_raiz__icontains=busca) |
            Q(solucao_aplicada__icontains=busca) |
            Q(observacao_encerramento__icontains=busca) |
            Q(sistema__nome__icontains=busca)
        )

    if sistema_id:
        ocorrencias = ocorrencias.filter(sistema_id=sistema_id)

    if unidade_id:
        if unidade_id == 'geral':
            ocorrencias = ocorrencias.filter(unidade__isnull=True)
        else:
            ocorrencias = ocorrencias.filter(unidade_id=unidade_id)

    if status:
        ocorrencias = ocorrencias.filter(status=status)

    if impacto:
        ocorrencias = ocorrencias.filter(impacto=impacto)

    if data_inicio:
        ocorrencias = ocorrencias.filter(encerrado_em__date__gte=data_inicio)

    if data_fim:
        ocorrencias = ocorrencias.filter(encerrado_em__date__lte=data_fim)

    return ocorrencias.order_by('-encerrado_em', '-atualizado_em')


def formatar_data_hora_csv(data_hora):
    if not data_hora:
        return ''

    try:
        return timezone.localtime(data_hora).strftime('%d/%m/%Y %H:%M')
    except Exception:
        return data_hora.strftime('%d/%m/%Y %H:%M')


def buscar_links_uteis_filtrados(request, modulo):
    pode_gerenciar = usuario_pode_gerenciar_links_uteis(request.user)

    if pode_gerenciar:
        links = ConteudoModulo.objects.filter(
            modulo=modulo,
            tipo='link'
        ).select_related(
            'unidade',
            'modulo'
        )
    else:
        links = buscar_conteudos_permitidos(
            request.user,
            modulo
        ).filter(
            tipo='link'
        ).select_related(
            'unidade',
            'modulo'
        )

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    status = request.GET.get('status', '').strip()

    if busca:
        links = links.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(link_externo__icontains=busca) |
            Q(unidade__nome__icontains=busca) |
            Q(unidade__sigla__icontains=busca)
        )

    if unidade_id:
        if unidade_id == 'geral':
            links = links.filter(unidade__isnull=True)
        else:
            links = links.filter(unidade_id=unidade_id)

    if pode_gerenciar:
        if status == 'ativo':
            links = links.filter(ativo=True)
        elif status == 'inativo':
            links = links.filter(ativo=False)
    else:
        links = links.filter(ativo=True)

    return links.order_by('ordem', 'titulo')


def buscar_manuais_filtrados(request, modulo):
    pode_gerenciar = usuario_pode_gerenciar_manuais(request.user)

    if pode_gerenciar:
        conteudos = ConteudoModulo.objects.filter(
            modulo=modulo
        ).select_related(
            'unidade',
            'modulo'
        ).prefetch_related(
            'grupos_permitidos'
        )
    else:
        conteudos = buscar_conteudos_permitidos(
            request.user,
            modulo
        ).select_related(
            'unidade',
            'modulo'
        ).prefetch_related(
            'grupos_permitidos'
        )

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    status = request.GET.get('status', '').strip()

    if busca:
        conteudos = conteudos.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(link_externo__icontains=busca) |
            Q(arquivo__icontains=busca) |
            Q(unidade__nome__icontains=busca) |
            Q(unidade__sigla__icontains=busca)
        )

    if unidade_id:
        if unidade_id == 'geral':
            conteudos = conteudos.filter(unidade__isnull=True)
        else:
            conteudos = conteudos.filter(unidade_id=unidade_id)

    if tipo:
        conteudos = conteudos.filter(tipo=tipo)

    if pode_gerenciar:
        if status == 'ativo':
            conteudos = conteudos.filter(ativo=True)
        elif status == 'inativo':
            conteudos = conteudos.filter(ativo=False)
    else:
        conteudos = conteudos.filter(ativo=True)

    return conteudos.order_by('tipo', 'ordem', 'titulo')


def buscar_dados_formularios_mv():
    return {
        'unidades': Unidade.objects.filter(ativo=True).order_by('nome'),
        'convenios': Convenio.objects.all().order_by('nome'),
        'convenios_ativos': Convenio.objects.filter(ativo=True).order_by('nome'),
        'planos': PlanoConvenio.objects.select_related('convenio').all().order_by('convenio__nome', 'nome'),
        'planos_ativos': PlanoConvenio.objects.filter(ativo=True).select_related('convenio').order_by('convenio__nome', 'nome'),
        'especialidades': Especialidade.objects.all().order_by('nome'),
        'especialidades_ativas': Especialidade.objects.filter(ativo=True).order_by('nome'),
    }



def usuario_pode_acessar_solicitacoes_ti(user):
    if usuario_eh_admin_ti(user):
        return True

    links_possiveis = [
        '/portal/modulos/solicitacoes-ti/',
        '/portal/modulos/solicitacoes-ti',
    ]

    nomes_possiveis = [
        'Solicitações de TI',
        'Solicitações Internas de TI',
        'Solicitações TI',
        'Chamados de TI',
    ]

    for link in links_possiveis:
        if usuario_pode_acessar_link_modulo(user, link):
            return True

    for nome in nomes_possiveis:
        if usuario_pode_acessar_modulo(user, nome):
            return True

    return False


def atualizar_sla_solicitacoes_dashboard(solicitacoes):
    for solicitacao in solicitacoes:
        if hasattr(solicitacao, 'atualizar_sla'):
            solicitacao.atualizar_sla(salvar=True)


def buscar_resumo_chamados_ti(user, limite=8, modulo_origem=None):
    chamados_base = SolicitacaoTI.objects.filter(
        ativo=True
    )

    if modulo_origem:
        chamados_base = chamados_base.filter(
            modulo_origem=modulo_origem
        )

    if not usuario_eh_admin_ti(user):
        chamados_base = chamados_base.filter(
            solicitante=user
        )

    chamados_para_atualizar_sla = chamados_base.exclude(
        status__in=['resolvido', 'cancelado']
    ).order_by(
        '-criado_em'
    )[:100]

    atualizar_sla_solicitacoes_dashboard(chamados_para_atualizar_sla)

    chamados_base = SolicitacaoTI.objects.filter(
        ativo=True
    )

    if modulo_origem:
        chamados_base = chamados_base.filter(
            modulo_origem=modulo_origem
        )

    if not usuario_eh_admin_ti(user):
        chamados_base = chamados_base.filter(
            solicitante=user
        )

    chamados_abertos_base = chamados_base.exclude(
        status__in=['resolvido', 'cancelado']
    )

    ultimos_chamados = chamados_base.select_related(
        'unidade',
        'setor',
        'solicitante',
        'responsavel_ti'
    ).order_by(
        '-criado_em'
    )[:limite]

    return {
        'total_chamados_ti': chamados_base.count(),
        'total_chamados_ti_abertos': chamados_base.filter(status='aberto').count(),
        'total_chamados_ti_atendimento': chamados_base.filter(status='em_atendimento').count(),
        'total_chamados_ti_aguardando': chamados_base.filter(
            Q(status='aguardando_usuario') |
            Q(status='aguardando_terceiro')
        ).count(),
        'total_chamados_ti_resolvidos': chamados_base.filter(status='resolvido').count(),
        'total_chamados_ti_sla_alerta': chamados_abertos_base.filter(
            sla_status='proximo_vencimento'
        ).count(),
        'total_chamados_ti_sla_estourado': chamados_abertos_base.filter(
            sla_status='estourado'
        ).count(),
        'total_chamados_ti_sem_responsavel': chamados_abertos_base.filter(
            responsavel_ti__isnull=True
        ).count(),
        'total_chamados_ti_criticos': chamados_abertos_base.filter(
            prioridade='critica'
        ).count(),
        'ultimos_chamados_ti': ultimos_chamados,
    }

def home(request):
    if request.user.is_authenticated:
        return redirect('portal')

    return render(request, 'core/home.html')


@login_required(login_url='/')
def portal(request):
    user = request.user
    unidade_usuario = obter_unidade_usuario(user)

    if usuario_eh_admin_ti(user):
        modulos = Modulo.objects.filter(ativo=True)
    else:
        grupos_usuario = user.groups.all()

        modulos = Modulo.objects.filter(
            ativo=True
        ).filter(
            Q(grupos_permitidos__in=grupos_usuario) |
            Q(grupos_permitidos__isnull=True)
        ).distinct()

    categorias = []

    for chave, nome in Modulo.CATEGORIA_CHOICES:
        itens = modulos.filter(categoria=chave).order_by('ordem', 'nome')

        if itens.exists():
            categorias.append({
                'chave': chave,
                'nome': nome,
                'modulos': itens,
            })

    ocorrencias_ativas = OcorrenciaSistema.objects.filter(
        ativo=True
    ).filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True)
    ).select_related(
        'sistema',
        'unidade'
    ).order_by(
        '-atualizado_em'
    )[:5]

    avisos_dashboard = buscar_avisos_dashboard(user)
    documentos_dashboard = buscar_documentos_dashboard(user)

    links_rapidos = ConteudoModulo.objects.none()
    ultimos_manuais = ConteudoModulo.objects.none()

    try:
        modulo_links = Modulo.objects.get(
            nome='Links Úteis / Sistemas Internos',
            ativo=True
        )

        if usuario_pode_acessar_modulo(user, modulo_links.nome):
            links_rapidos = buscar_conteudos_permitidos(
                user,
                modulo_links
            ).filter(
                tipo='link'
            ).select_related(
                'unidade'
            ).order_by(
                'ordem',
                'titulo'
            )[:6]

    except Modulo.DoesNotExist:
        pass

    try:
        modulo_manuais = Modulo.objects.get(
            nome='Manuais e Procedimentos',
            ativo=True
        )

        if usuario_pode_acessar_modulo(user, modulo_manuais.nome):
            ultimos_manuais = buscar_conteudos_permitidos(
                user,
                modulo_manuais
            ).select_related(
                'unidade'
            ).order_by(
                '-atualizado_em',
                'titulo'
            )[:5]

    except Modulo.DoesNotExist:
        pass


    pode_acessar_solicitacoes_ti = usuario_pode_acessar_solicitacoes_ti(user)

    resumo_chamados_ti = {
        'total_chamados_ti': 0,
        'total_chamados_ti_abertos': 0,
        'total_chamados_ti_atendimento': 0,
        'total_chamados_ti_aguardando': 0,
        'total_chamados_ti_resolvidos': 0,
        'total_chamados_ti_sla_alerta': 0,
        'total_chamados_ti_sla_estourado': 0,
        'total_chamados_ti_sem_responsavel': 0,
        'total_chamados_ti_criticos': 0,
        'ultimos_chamados_ti': SolicitacaoTI.objects.none(),
    }

    if pode_acessar_solicitacoes_ti:
        resumo_chamados_ti = buscar_resumo_chamados_ti(user)
    return render(request, 'core/portal.html', {
        'page_title': 'Portal',
        'categorias': categorias,
        'ocorrencias_ativas': ocorrencias_ativas,
        'avisos_dashboard': avisos_dashboard,
        'documentos_dashboard': documentos_dashboard,
        'links_rapidos': links_rapidos,
        'ultimos_manuais': ultimos_manuais,
        'total_modulos': modulos.count(),
        'total_ocorrencias': len(ocorrencias_ativas),
        'total_avisos': len(avisos_dashboard),
        'total_documentos_alerta': len(documentos_dashboard),
        'total_links': len(links_rapidos),
        'total_manuais': len(ultimos_manuais),
        'acessos_botoes_rapidos': montar_acessos_botoes_rapidos(user),
        'pode_acessar_solicitacoes_ti': pode_acessar_solicitacoes_ti,
        **resumo_chamados_ti,
        'pode_acessar_administracao': usuario_pode_acessar_administracao(user),
    })


@login_required(login_url='/')
def modulo_mv(request):
    nome_modulo = 'MV / Sistema Hospitalar'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    conteudos = buscar_conteudos_permitidos(request.user, modulo)
    pode_gerenciar_mv = usuario_pode_gerenciar_mv(request.user)

    conteudos_por_tipo = {
        'manual': conteudos.filter(tipo='manual'),
        'convenio': conteudos.filter(tipo='convenio'),
        'contingencia': conteudos.filter(tipo='contingencia'),
        'link': conteudos.filter(tipo='link'),
        'chamado': conteudos.filter(tipo='chamado'),
        'observacao': conteudos.filter(tipo='observacao'),
    }

    total_convenios = Convenio.objects.count()
    total_convenios_ativos = Convenio.objects.filter(ativo=True).count()
    total_planos = PlanoConvenio.objects.count()
    total_regras_ativas = RegraAtendimentoConvenio.objects.filter(ativo=True).count()
    total_procedimentos_proibidos = ProcedimentoProibidoPlano.objects.filter(ativo=True).count()

    chamados_mv_base = SolicitacaoTI.objects.filter(
        ativo=True,
        modulo_origem='mv'
    )

    if not usuario_eh_admin_ti(request.user):
        chamados_mv_base = chamados_mv_base.filter(
            solicitante=request.user
        )

    chamados_mv = chamados_mv_base.select_related(
        'unidade',
        'setor',
        'solicitante',
        'responsavel_ti'
    ).order_by(
        '-criado_em'
    )[:8]

    total_chamados_mv_abertos = chamados_mv_base.exclude(
        status__in=['resolvido', 'cancelado']
    ).count()

    total_chamados_mv_atendimento = chamados_mv_base.filter(
        status='em_atendimento'
    ).count()

    total_chamados_mv_resolvidos = chamados_mv_base.filter(
        status='resolvido'
    ).count()

    return render(request, 'core/modulo_mv.html', {
        'modulo': modulo,
        'conteudos_por_tipo': conteudos_por_tipo,
        'pode_gerenciar_mv': pode_gerenciar_mv,
        'chamados_mv': chamados_mv,
        'total_chamados_mv_abertos': total_chamados_mv_abertos,
        'total_chamados_mv_atendimento': total_chamados_mv_atendimento,
        'total_chamados_mv_resolvidos': total_chamados_mv_resolvidos,
        'total_convenios': total_convenios,
        'total_convenios_ativos': total_convenios_ativos,
        'total_planos': total_planos,
        'total_regras_ativas': total_regras_ativas,
        'total_procedimentos_proibidos': total_procedimentos_proibidos,
    })


@login_required(login_url='/')
def mv_manuais(request):
    nome_modulo = 'MV / Sistema Hospitalar'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudos = buscar_conteudos_permitidos(request.user, modulo).filter(
        tipo='manual'
    )

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()

    if busca:
        conteudos = conteudos.filter(
            Q(titulo__icontains=busca) |
            Q(descricao__icontains=busca)
        )

    if unidade_id:
        if unidade_id == 'geral':
            conteudos = conteudos.filter(unidade__isnull=True)
        else:
            conteudos = conteudos.filter(unidade_id=unidade_id)

    unidades = Unidade.objects.filter(ativo=True).order_by('nome')

    return render(request, 'core/mv_manuais.html', {
        'modulo': modulo,
        'conteudos': conteudos,
        'unidades': unidades,
        'busca': busca,
        'unidade_id': unidade_id,
    })


@login_required(login_url='/')
def mv_convenios(request):
    nome_modulo = 'MV / Sistema Hospitalar'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    pode_gerenciar_mv = usuario_pode_gerenciar_mv(request.user)

    regras = RegraAtendimentoConvenio.objects.select_related(
        'unidade',
        'convenio',
        'plano',
        'especialidade',
    )

    proibicoes = ProcedimentoProibidoPlano.objects.select_related(
        'convenio',
        'plano',
    )

    if not pode_gerenciar_mv:
        regras = regras.filter(ativo=True)
        proibicoes = proibicoes.filter(ativo=True)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    convenio_id = request.GET.get('convenio', '').strip()
    plano_id = request.GET.get('plano', '').strip()
    tipo_atendimento = request.GET.get('tipo_atendimento', '').strip()
    especialidade_id = request.GET.get('especialidade', '').strip()
    status = request.GET.get('status', '').strip()
    procedimento = request.GET.get('procedimento', '').strip()

    if busca:
        regras = regras.filter(
            Q(convenio__nome__icontains=busca) |
            Q(convenio__codigo_mv__icontains=busca) |
            Q(plano__nome__icontains=busca) |
            Q(plano__codigo_mv__icontains=busca) |
            Q(especialidade__nome__icontains=busca) |
            Q(observacao__icontains=busca)
        )

    if unidade_id:
        regras = regras.filter(unidade_id=unidade_id)

    if convenio_id:
        regras = regras.filter(convenio_id=convenio_id)
        proibicoes = proibicoes.filter(convenio_id=convenio_id)

    if plano_id:
        regras = regras.filter(plano_id=plano_id)
        proibicoes = proibicoes.filter(plano_id=plano_id)

    if tipo_atendimento:
        regras = regras.filter(tipo_atendimento=tipo_atendimento)

    if especialidade_id:
        regras = regras.filter(especialidade_id=especialidade_id)

    if status:
        regras = regras.filter(status=status)

    if procedimento:
        proibicoes = proibicoes.filter(
            Q(codigo_procedimento__icontains=procedimento) |
            Q(descricao_procedimento__icontains=procedimento)
        )
    else:
        proibicoes = proibicoes.none()

    regras = regras.order_by(
        'unidade__nome',
        'convenio__nome',
        'plano__nome',
        'tipo_atendimento',
        'especialidade__nome',
    )

    proibicoes = proibicoes.order_by(
        'convenio__nome',
        'plano__nome',
        'descricao_procedimento',
    )


    resumo_chamados_mv = buscar_resumo_chamados_ti(
        request.user,
        limite=8,
        modulo_origem='mv'
    )

    chamados_mv = resumo_chamados_mv['ultimos_chamados_ti']
    total_chamados_mv_abertos = (
        resumo_chamados_mv['total_chamados_ti_abertos'] +
        resumo_chamados_mv['total_chamados_ti_atendimento'] +
        resumo_chamados_mv['total_chamados_ti_aguardando']
    )
    total_chamados_mv_atendimento = resumo_chamados_mv['total_chamados_ti_atendimento']
    total_chamados_mv_resolvidos = resumo_chamados_mv['total_chamados_ti_resolvidos']
    return render(request, 'core/mv_convenios.html', {
        'regras': regras,
        'proibicoes': proibicoes,
        'unidades': Unidade.objects.filter(ativo=True).order_by('nome'),
        'convenios': Convenio.objects.filter(ativo=True).order_by('nome'),
        'planos': PlanoConvenio.objects.filter(ativo=True).select_related('convenio').order_by('convenio__nome', 'nome'),
        'especialidades': Especialidade.objects.filter(ativo=True).order_by('nome'),
        'todos_convenios': Convenio.objects.all().order_by('nome'),
        'todos_planos': PlanoConvenio.objects.select_related('convenio').all().order_by('convenio__nome', 'nome'),
        'todas_especialidades': Especialidade.objects.all().order_by('nome'),
        'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
        'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
        'busca': busca,
        'unidade_id': unidade_id,
        'convenio_id': convenio_id,
        'plano_id': plano_id,
        'tipo_atendimento': tipo_atendimento,
        'especialidade_id': especialidade_id,
        'status': status,
        'procedimento': procedimento,
        'pode_gerenciar_mv': pode_gerenciar_mv,
        'chamados_mv': chamados_mv,
        'total_chamados_mv_abertos': total_chamados_mv_abertos,
        'total_chamados_mv_atendimento': total_chamados_mv_atendimento,
        'total_chamados_mv_resolvidos': total_chamados_mv_resolvidos,
        'total_convenios': Convenio.objects.count(),
        'total_planos': PlanoConvenio.objects.count(),
        'total_especialidades': Especialidade.objects.count(),
        'total_regras': RegraAtendimentoConvenio.objects.count(),
        'total_procedimentos': ProcedimentoProibidoPlano.objects.count(),
    })


@login_required(login_url='/')
def novo_convenio_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'codigo_mv': '',
        'nome': '',
        'tipo_mv': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_convenio(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do convênio.')

        if Convenio.objects.filter(nome__iexact=form_data['nome']).exists():
            erros.append('Já existe um convênio com este nome.')

        if form_data['codigo_mv'] and Convenio.objects.filter(codigo_mv=form_data['codigo_mv']).exists():
            erros.append('Já existe um convênio com este código MV.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_convenio_mv.html', {
                'titulo': 'Novo convênio MV',
                'subtitulo': 'Cadastre um convênio utilizado no MV.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/convenios/novo/',
                'modo': 'novo',
            })

        convenio = Convenio.objects.create(
            codigo_mv=form_data['codigo_mv'],
            nome=form_data['nome'],
            tipo_mv=form_data['tipo_mv'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_convenio_mv(
            request,
            convenio,
            'criado',
            f'Convênio MV criado: {convenio.nome}'
        )

        messages.success(request, 'Convênio cadastrado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_convenio_mv.html', {
        'titulo': 'Novo convênio MV',
        'subtitulo': 'Cadastre um convênio utilizado no MV.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/convenios/novo/',
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_convenio_mv(request, convenio_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    convenio = get_object_or_404(Convenio, id=convenio_id)
    form_data = convenio_para_form_data(convenio)

    if request.method == 'POST':
        form_data = montar_form_data_convenio(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do convênio.')

        if Convenio.objects.filter(nome__iexact=form_data['nome']).exclude(id=convenio.id).exists():
            erros.append('Já existe outro convênio com este nome.')

        if form_data['codigo_mv'] and Convenio.objects.filter(codigo_mv=form_data['codigo_mv']).exclude(id=convenio.id).exists():
            erros.append('Já existe outro convênio com este código MV.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_convenio_mv.html', {
                'titulo': 'Editar convênio MV',
                'subtitulo': 'Atualize os dados do convênio.',
                'form_data': form_data,
                'convenio_editado': convenio,
                'url_salvar': f'/portal/modulos/mv/convenios/editar/{convenio.id}/',
                'modo': 'editar',
            })

        convenio.codigo_mv = form_data['codigo_mv']
        convenio.nome = form_data['nome']
        convenio.tipo_mv = form_data['tipo_mv']
        convenio.ativo = form_data['ativo']
        convenio.save()

        registrar_auditoria_convenio_mv(
            request,
            convenio,
            'alterado',
            f'Convênio MV alterado: {convenio.nome}'
        )

        messages.success(request, 'Convênio atualizado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_convenio_mv.html', {
        'titulo': 'Editar convênio MV',
        'subtitulo': 'Atualize os dados do convênio.',
        'form_data': form_data,
        'convenio_editado': convenio,
        'url_salvar': f'/portal/modulos/mv/convenios/editar/{convenio.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_convenio_mv(request, convenio_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    convenio = get_object_or_404(Convenio, id=convenio_id)
    convenio.ativo = False
    convenio.save()

    registrar_auditoria_convenio_mv(request, convenio, 'alterado', f'Convênio MV inativado: {convenio.nome}')
    messages.success(request, 'Convênio inativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def reativar_convenio_mv(request, convenio_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    convenio = get_object_or_404(Convenio, id=convenio_id)
    convenio.ativo = True
    convenio.save()

    registrar_auditoria_convenio_mv(request, convenio, 'alterado', f'Convênio MV reativado: {convenio.nome}')
    messages.success(request, 'Convênio reativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def novo_plano_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    dados = buscar_dados_formularios_mv()

    form_data = {
        'convenio': '',
        'codigo_mv': '',
        'nome': '',
        'regra_codigo_mv': '',
        'regra_nome_mv': '',
        'indice_codigo_mv': '',
        'indice_nome_mv': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_plano(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['nome']:
            erros.append('Informe o nome do plano.')

        if form_data['convenio'] and form_data['codigo_mv']:
            if PlanoConvenio.objects.filter(convenio_id=form_data['convenio'], codigo_mv=form_data['codigo_mv']).exists():
                erros.append('Já existe um plano com este código MV para o convênio selecionado.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_plano_mv.html', {
                'titulo': 'Novo plano MV',
                'subtitulo': 'Cadastre um plano vinculado ao convênio.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/planos/novo/',
                **dados,
                'modo': 'novo',
            })

        plano = PlanoConvenio.objects.create(
            convenio_id=form_data['convenio'],
            codigo_mv=form_data['codigo_mv'],
            nome=form_data['nome'],
            regra_codigo_mv=form_data['regra_codigo_mv'],
            regra_nome_mv=form_data['regra_nome_mv'],
            indice_codigo_mv=form_data['indice_codigo_mv'],
            indice_nome_mv=form_data['indice_nome_mv'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_plano_mv(request, plano, 'criado', f'Plano MV criado: {plano.nome}')
        messages.success(request, 'Plano cadastrado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_plano_mv.html', {
        'titulo': 'Novo plano MV',
        'subtitulo': 'Cadastre um plano vinculado ao convênio.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/planos/novo/',
        **dados,
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_plano_mv(request, plano_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    plano = get_object_or_404(PlanoConvenio.objects.select_related('convenio'), id=plano_id)
    dados = buscar_dados_formularios_mv()
    form_data = plano_para_form_data(plano)

    if request.method == 'POST':
        form_data = montar_form_data_plano(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['nome']:
            erros.append('Informe o nome do plano.')

        if form_data['convenio'] and form_data['codigo_mv']:
            if PlanoConvenio.objects.filter(
                convenio_id=form_data['convenio'],
                codigo_mv=form_data['codigo_mv']
            ).exclude(id=plano.id).exists():
                erros.append('Já existe outro plano com este código MV para o convênio selecionado.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_plano_mv.html', {
                'titulo': 'Editar plano MV',
                'subtitulo': 'Atualize os dados do plano.',
                'form_data': form_data,
                'plano_editado': plano,
                'url_salvar': f'/portal/modulos/mv/planos/editar/{plano.id}/',
                **dados,
                'modo': 'editar',
            })

        plano.convenio_id = form_data['convenio']
        plano.codigo_mv = form_data['codigo_mv']
        plano.nome = form_data['nome']
        plano.regra_codigo_mv = form_data['regra_codigo_mv']
        plano.regra_nome_mv = form_data['regra_nome_mv']
        plano.indice_codigo_mv = form_data['indice_codigo_mv']
        plano.indice_nome_mv = form_data['indice_nome_mv']
        plano.ativo = form_data['ativo']
        plano.save()

        registrar_auditoria_plano_mv(request, plano, 'alterado', f'Plano MV alterado: {plano.nome}')
        messages.success(request, 'Plano atualizado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_plano_mv.html', {
        'titulo': 'Editar plano MV',
        'subtitulo': 'Atualize os dados do plano.',
        'form_data': form_data,
        'plano_editado': plano,
        'url_salvar': f'/portal/modulos/mv/planos/editar/{plano.id}/',
        **dados,
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_plano_mv(request, plano_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    plano = get_object_or_404(PlanoConvenio.objects.select_related('convenio'), id=plano_id)
    plano.ativo = False
    plano.save()

    registrar_auditoria_plano_mv(request, plano, 'alterado', f'Plano MV inativado: {plano.nome}')
    messages.success(request, 'Plano inativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def reativar_plano_mv(request, plano_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    plano = get_object_or_404(PlanoConvenio.objects.select_related('convenio'), id=plano_id)
    plano.ativo = True
    plano.save()

    registrar_auditoria_plano_mv(request, plano, 'alterado', f'Plano MV reativado: {plano.nome}')
    messages.success(request, 'Plano reativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def nova_especialidade_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'nome': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_especialidade(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome da especialidade.')

        if Especialidade.objects.filter(nome__iexact=form_data['nome']).exists():
            erros.append('Já existe uma especialidade com este nome.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_especialidade_mv.html', {
                'titulo': 'Nova especialidade MV',
                'subtitulo': 'Cadastre uma especialidade para uso nas regras de convênio.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/especialidades/nova/',
                'modo': 'novo',
            })

        especialidade = Especialidade.objects.create(
            nome=form_data['nome'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_especialidade_mv(request, especialidade, 'criado', f'Especialidade MV criada: {especialidade.nome}')
        messages.success(request, 'Especialidade cadastrada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_especialidade_mv.html', {
        'titulo': 'Nova especialidade MV',
        'subtitulo': 'Cadastre uma especialidade para uso nas regras de convênio.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/especialidades/nova/',
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_especialidade_mv(request, especialidade_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    especialidade = get_object_or_404(Especialidade, id=especialidade_id)
    form_data = especialidade_para_form_data(especialidade)

    if request.method == 'POST':
        form_data = montar_form_data_especialidade(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome da especialidade.')

        if Especialidade.objects.filter(nome__iexact=form_data['nome']).exclude(id=especialidade.id).exists():
            erros.append('Já existe outra especialidade com este nome.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_especialidade_mv.html', {
                'titulo': 'Editar especialidade MV',
                'subtitulo': 'Atualize os dados da especialidade.',
                'form_data': form_data,
                'especialidade_editada': especialidade,
                'url_salvar': f'/portal/modulos/mv/especialidades/editar/{especialidade.id}/',
                'modo': 'editar',
            })

        especialidade.nome = form_data['nome']
        especialidade.ativo = form_data['ativo']
        especialidade.save()

        registrar_auditoria_especialidade_mv(request, especialidade, 'alterado', f'Especialidade MV alterada: {especialidade.nome}')
        messages.success(request, 'Especialidade atualizada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_especialidade_mv.html', {
        'titulo': 'Editar especialidade MV',
        'subtitulo': 'Atualize os dados da especialidade.',
        'form_data': form_data,
        'especialidade_editada': especialidade,
        'url_salvar': f'/portal/modulos/mv/especialidades/editar/{especialidade.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_especialidade_mv(request, especialidade_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    especialidade = get_object_or_404(Especialidade, id=especialidade_id)
    especialidade.ativo = False
    especialidade.save()

    registrar_auditoria_especialidade_mv(request, especialidade, 'alterado', f'Especialidade MV inativada: {especialidade.nome}')
    messages.success(request, 'Especialidade inativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def reativar_especialidade_mv(request, especialidade_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    especialidade = get_object_or_404(Especialidade, id=especialidade_id)
    especialidade.ativo = True
    especialidade.save()

    registrar_auditoria_especialidade_mv(request, especialidade, 'alterado', f'Especialidade MV reativada: {especialidade.nome}')
    messages.success(request, 'Especialidade reativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def nova_regra_convenio_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    dados = buscar_dados_formularios_mv()

    form_data = {
        'unidade': '',
        'convenio': '',
        'plano': '',
        'tipo_atendimento': 'consulta',
        'especialidade': '',
        'status': 'aceito',
        'exige_autorizacao': False,
        'observacao': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_regra(request)
        erros = []

        if not form_data['unidade']:
            erros.append('Informe a unidade.')

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['tipo_atendimento']:
            erros.append('Informe o tipo de atendimento.')

        if not form_data['status']:
            erros.append('Informe o status da regra.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_regra_convenio_mv.html', {
                'titulo': 'Nova regra de convênio',
                'subtitulo': 'Cadastre uma regra manual de atendimento.',
                'form_data': form_data,
                'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
                'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
                'url_salvar': '/portal/modulos/mv/regras/nova/',
                **dados,
                'modo': 'novo',
            })

        regra = RegraAtendimentoConvenio.objects.create(
            unidade_id=form_data['unidade'],
            convenio_id=form_data['convenio'],
            plano_id=form_data['plano'],
            tipo_atendimento=form_data['tipo_atendimento'],
            especialidade_id=form_data['especialidade'] or None,
            status=form_data['status'],
            exige_autorizacao=form_data['exige_autorizacao'],
            observacao=form_data['observacao'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_regra_mv(request, regra, 'criado', f'Regra de convênio criada: {regra}')
        messages.success(request, 'Regra cadastrada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_regra_convenio_mv.html', {
        'titulo': 'Nova regra de convênio',
        'subtitulo': 'Cadastre uma regra manual de atendimento.',
        'form_data': form_data,
        'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
        'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
        'url_salvar': '/portal/modulos/mv/regras/nova/',
        **dados,
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_regra_convenio_mv(request, regra_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    regra = get_object_or_404(
        RegraAtendimentoConvenio.objects.select_related('unidade', 'convenio', 'plano', 'especialidade'),
        id=regra_id
    )

    dados = buscar_dados_formularios_mv()
    form_data = regra_para_form_data(regra)

    if request.method == 'POST':
        form_data = montar_form_data_regra(request)
        erros = []

        if not form_data['unidade']:
            erros.append('Informe a unidade.')

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['tipo_atendimento']:
            erros.append('Informe o tipo de atendimento.')

        if not form_data['status']:
            erros.append('Informe o status da regra.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_regra_convenio_mv.html', {
                'titulo': 'Editar regra de convênio',
                'subtitulo': 'Atualize a regra manual de atendimento.',
                'form_data': form_data,
                'regra_editada': regra,
                'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
                'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
                'url_salvar': f'/portal/modulos/mv/regras/editar/{regra.id}/',
                **dados,
                'modo': 'editar',
            })

        regra.unidade_id = form_data['unidade']
        regra.convenio_id = form_data['convenio']
        regra.plano_id = form_data['plano']
        regra.tipo_atendimento = form_data['tipo_atendimento']
        regra.especialidade_id = form_data['especialidade'] or None
        regra.status = form_data['status']
        regra.exige_autorizacao = form_data['exige_autorizacao']
        regra.observacao = form_data['observacao']
        regra.ativo = form_data['ativo']
        regra.save()

        registrar_auditoria_regra_mv(request, regra, 'alterado', f'Regra de convênio alterada: {regra}')
        messages.success(request, 'Regra atualizada com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_regra_convenio_mv.html', {
        'titulo': 'Editar regra de convênio',
        'subtitulo': 'Atualize a regra manual de atendimento.',
        'form_data': form_data,
        'regra_editada': regra,
        'tipos_atendimento': RegraAtendimentoConvenio.TIPO_ATENDIMENTO_CHOICES,
        'status_choices': RegraAtendimentoConvenio.STATUS_CHOICES,
        'url_salvar': f'/portal/modulos/mv/regras/editar/{regra.id}/',
        **dados,
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_regra_convenio_mv(request, regra_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    regra = get_object_or_404(RegraAtendimentoConvenio, id=regra_id)
    regra.ativo = False
    regra.save()

    registrar_auditoria_regra_mv(request, regra, 'alterado', f'Regra de convênio inativada: {regra}')
    messages.success(request, 'Regra inativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def reativar_regra_convenio_mv(request, regra_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    regra = get_object_or_404(RegraAtendimentoConvenio, id=regra_id)
    regra.ativo = True
    regra.save()

    registrar_auditoria_regra_mv(request, regra, 'alterado', f'Regra de convênio reativada: {regra}')
    messages.success(request, 'Regra reativada com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def novo_procedimento_proibido_mv(request):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    dados = buscar_dados_formularios_mv()

    form_data = {
        'convenio': '',
        'plano': '',
        'codigo_procedimento': '',
        'descricao_procedimento': '',
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_procedimento(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['codigo_procedimento']:
            erros.append('Informe o código do procedimento.')

        if not form_data['descricao_procedimento']:
            erros.append('Informe a descrição do procedimento.')

        if form_data['plano'] and form_data['codigo_procedimento']:
            if ProcedimentoProibidoPlano.objects.filter(
                plano_id=form_data['plano'],
                codigo_procedimento=form_data['codigo_procedimento']
            ).exists():
                erros.append('Este procedimento já está cadastrado como proibido para este plano.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_procedimento_proibido_mv.html', {
                'titulo': 'Novo procedimento proibido',
                'subtitulo': 'Cadastre um procedimento proibido por plano.',
                'form_data': form_data,
                'url_salvar': '/portal/modulos/mv/procedimentos-proibidos/novo/',
                **dados,
                'modo': 'novo',
            })

        procedimento = ProcedimentoProibidoPlano.objects.create(
            convenio_id=form_data['convenio'],
            plano_id=form_data['plano'],
            codigo_procedimento=form_data['codigo_procedimento'],
            descricao_procedimento=form_data['descricao_procedimento'],
            ativo=form_data['ativo'],
        )

        registrar_auditoria_procedimento_mv(
            request,
            procedimento,
            'criado',
            f'Procedimento proibido criado: {procedimento.codigo_procedimento}'
        )

        messages.success(request, 'Procedimento proibido cadastrado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_procedimento_proibido_mv.html', {
        'titulo': 'Novo procedimento proibido',
        'subtitulo': 'Cadastre um procedimento proibido por plano.',
        'form_data': form_data,
        'url_salvar': '/portal/modulos/mv/procedimentos-proibidos/novo/',
        **dados,
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_procedimento_proibido_mv(request, procedimento_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    procedimento = get_object_or_404(
        ProcedimentoProibidoPlano.objects.select_related('convenio', 'plano'),
        id=procedimento_id
    )

    dados = buscar_dados_formularios_mv()
    form_data = procedimento_para_form_data(procedimento)

    if request.method == 'POST':
        form_data = montar_form_data_procedimento(request)
        erros = []

        if not form_data['convenio']:
            erros.append('Informe o convênio.')

        if not form_data['plano']:
            erros.append('Informe o plano.')

        if not form_data['codigo_procedimento']:
            erros.append('Informe o código do procedimento.')

        if not form_data['descricao_procedimento']:
            erros.append('Informe a descrição do procedimento.')

        if form_data['plano'] and form_data['codigo_procedimento']:
            if ProcedimentoProibidoPlano.objects.filter(
                plano_id=form_data['plano'],
                codigo_procedimento=form_data['codigo_procedimento']
            ).exclude(id=procedimento.id).exists():
                erros.append('Outro procedimento com este código já está cadastrado como proibido para este plano.')

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_procedimento_proibido_mv.html', {
                'titulo': 'Editar procedimento proibido',
                'subtitulo': 'Atualize o procedimento proibido.',
                'form_data': form_data,
                'procedimento_editado': procedimento,
                'url_salvar': f'/portal/modulos/mv/procedimentos-proibidos/editar/{procedimento.id}/',
                **dados,
                'modo': 'editar',
            })

        procedimento.convenio_id = form_data['convenio']
        procedimento.plano_id = form_data['plano']
        procedimento.codigo_procedimento = form_data['codigo_procedimento']
        procedimento.descricao_procedimento = form_data['descricao_procedimento']
        procedimento.ativo = form_data['ativo']
        procedimento.save()

        registrar_auditoria_procedimento_mv(
            request,
            procedimento,
            'alterado',
            f'Procedimento proibido alterado: {procedimento.codigo_procedimento}'
        )

        messages.success(request, 'Procedimento proibido atualizado com sucesso.')
        return redirect('/portal/modulos/mv/convenios/')

    return render(request, 'core/formulario_procedimento_proibido_mv.html', {
        'titulo': 'Editar procedimento proibido',
        'subtitulo': 'Atualize o procedimento proibido.',
        'form_data': form_data,
        'procedimento_editado': procedimento,
        'url_salvar': f'/portal/modulos/mv/procedimentos-proibidos/editar/{procedimento.id}/',
        **dados,
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_procedimento_proibido_mv(request, procedimento_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    procedimento = get_object_or_404(
        ProcedimentoProibidoPlano.objects.select_related('convenio', 'plano'),
        id=procedimento_id
    )

    procedimento.ativo = False
    procedimento.save()

    registrar_auditoria_procedimento_mv(
        request,
        procedimento,
        'alterado',
        f'Procedimento proibido inativado: {procedimento.codigo_procedimento}'
    )

    messages.success(request, 'Procedimento proibido inativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def reativar_procedimento_proibido_mv(request, procedimento_id):
    if not usuario_pode_gerenciar_mv(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    procedimento = get_object_or_404(
        ProcedimentoProibidoPlano.objects.select_related('convenio', 'plano'),
        id=procedimento_id
    )

    procedimento.ativo = True
    procedimento.save()

    registrar_auditoria_procedimento_mv(
        request,
        procedimento,
        'alterado',
        f'Procedimento proibido reativado: {procedimento.codigo_procedimento}'
    )

    messages.success(request, 'Procedimento proibido reativado com sucesso.')
    return redirect('/portal/modulos/mv/convenios/')


@login_required(login_url='/')
def status_sistemas(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    pode_gerenciar = usuario_pode_gerenciar_status(request.user)
    unidade_usuario = obter_unidade_usuario(request.user)

    ocorrencias_visiveis = OcorrenciaSistema.objects.filter(
        ativo=True
    ).filter(
        Q(unidade=unidade_usuario) |
        Q(unidade__isnull=True)
    ).select_related(
        'sistema',
        'unidade'
    ).order_by(
        '-atualizado_em'
    )

    if pode_gerenciar:
        sistemas = SistemaMonitorado.objects.all()
    else:
        sistemas = SistemaMonitorado.objects.filter(ativo=True)

    sistemas = sistemas.prefetch_related(
        Prefetch(
            'ocorrencias',
            queryset=ocorrencias_visiveis,
            to_attr='ocorrencias_visiveis'
        )
    ).order_by(
        'ordem',
        'nome'
    )

    resumo = {
        'operacional': 0,
        'instavel': 0,
        'indisponivel': 0,
        'manutencao': 0,
    }

    for sistema in sistemas:
        if sistema.ocorrencias_visiveis:
            status_atual = sistema.ocorrencias_visiveis[0].status
        else:
            status_atual = 'operacional'

        sistema.status_atual = status_atual

        if status_atual in resumo:
            resumo[status_atual] += 1
        else:
            resumo['operacional'] += 1

    return render(request, 'core/status_sistemas.html', {
        'page_title': 'Status dos Sistemas',
        'sistemas': sistemas,
        'ocorrencias_ativas': ocorrencias_visiveis,
        'resumo': resumo,
        'pode_gerenciar_status': pode_gerenciar,
        'total_sistemas': sistemas.count(),
        'total_sistemas_ativos': sistemas.filter(ativo=True).count(),
        'total_sistemas_inativos': sistemas.filter(ativo=False).count() if pode_gerenciar else 0,
    })


@login_required(login_url='/')
def novo_sistema_monitorado(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    form_data = {
        'nome': '',
        'descricao': '',
        'categoria': 'infraestrutura',
        'icone': '🖥️',
        'ordem': 0,
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_sistema(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do sistema.')

        if not form_data['categoria']:
            erros.append('Informe a categoria.')

        if SistemaMonitorado.objects.filter(nome__iexact=form_data['nome']).exists():
            erros.append('Já existe um sistema cadastrado com este nome.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_sistema_monitorado.html', {
                'titulo': 'Novo sistema monitorado',
                'subtitulo': 'Cadastre um sistema, serviço, link, servidor ou fornecedor monitorado pela TI.',
                'form_data': form_data,
                'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
                'url_salvar': '/portal/modulos/status-sistemas/sistema/novo/',
                'modo': 'novo',
            })

        sistema = SistemaMonitorado.objects.create(
            nome=form_data['nome'],
            descricao=form_data['descricao'],
            categoria=form_data['categoria'],
            icone=form_data['icone'],
            ordem=ordem,
            ativo=form_data['ativo'],
        )

        registrar_auditoria_sistema(
            request=request,
            sistema=sistema,
            acao='criado',
            titulo=f'Sistema monitorado criado: {sistema.nome}'
        )

        messages.success(request, 'Sistema monitorado cadastrado com sucesso.')
        return redirect('/portal/modulos/status-sistemas/')

    return render(request, 'core/formulario_sistema_monitorado.html', {
        'titulo': 'Novo sistema monitorado',
        'subtitulo': 'Cadastre um sistema, serviço, link, servidor ou fornecedor monitorado pela TI.',
        'form_data': form_data,
        'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
        'url_salvar': '/portal/modulos/status-sistemas/sistema/novo/',
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_sistema_monitorado(request, sistema_id):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistema = get_object_or_404(SistemaMonitorado, id=sistema_id)
    form_data = sistema_para_form_data(sistema)

    if request.method == 'POST':
        form_data = montar_form_data_sistema(request)
        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do sistema.')

        if not form_data['categoria']:
            erros.append('Informe a categoria.')

        if SistemaMonitorado.objects.filter(nome__iexact=form_data['nome']).exclude(id=sistema.id).exists():
            erros.append('Já existe outro sistema cadastrado com este nome.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_sistema_monitorado.html', {
                'titulo': 'Editar sistema monitorado',
                'subtitulo': 'Atualize o sistema selecionado.',
                'form_data': form_data,
                'sistema_editado': sistema,
                'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
                'url_salvar': f'/portal/modulos/status-sistemas/sistema/editar/{sistema.id}/',
                'modo': 'editar',
            })

        sistema.nome = form_data['nome']
        sistema.descricao = form_data['descricao']
        sistema.categoria = form_data['categoria']
        sistema.icone = form_data['icone']
        sistema.ordem = ordem
        sistema.ativo = form_data['ativo']
        sistema.save()

        registrar_auditoria_sistema(
            request=request,
            sistema=sistema,
            acao='alterado',
            titulo=f'Sistema monitorado alterado: {sistema.nome}'
        )

        messages.success(request, 'Sistema monitorado atualizado com sucesso.')
        return redirect('/portal/modulos/status-sistemas/')

    return render(request, 'core/formulario_sistema_monitorado.html', {
        'titulo': 'Editar sistema monitorado',
        'subtitulo': 'Atualize o sistema selecionado.',
        'form_data': form_data,
        'sistema_editado': sistema,
        'categorias': SistemaMonitorado.CATEGORIA_CHOICES,
        'url_salvar': f'/portal/modulos/status-sistemas/sistema/editar/{sistema.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_sistema_monitorado(request, sistema_id):
    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistema = get_object_or_404(SistemaMonitorado, id=sistema_id)
    sistema.ativo = False
    sistema.save()

    registrar_auditoria_sistema(
        request=request,
        sistema=sistema,
        acao='alterado',
        titulo=f'Sistema monitorado inativado: {sistema.nome}'
    )

    messages.success(request, 'Sistema monitorado inativado com sucesso.')
    return redirect('/portal/modulos/status-sistemas/')


@login_required(login_url='/')
def reativar_sistema_monitorado(request, sistema_id):
    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistema = get_object_or_404(SistemaMonitorado, id=sistema_id)
    sistema.ativo = True
    sistema.save()

    registrar_auditoria_sistema(
        request=request,
        sistema=sistema,
        acao='alterado',
        titulo=f'Sistema monitorado reativado: {sistema.nome}'
    )

    messages.success(request, 'Sistema monitorado reativado com sucesso.')
    return redirect('/portal/modulos/status-sistemas/')


@login_required(login_url='/')
def historico_ocorrencias_status(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    ocorrencias_filtradas = filtrar_ocorrencias_historico(request, request.user)

    sistemas = SistemaMonitorado.objects.filter(
        ativo=True
    ).order_by(
        'ordem',
        'nome'
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    total_ocorrencias = ocorrencias_filtradas.count()
    ocorrencias = ocorrencias_filtradas[:300]

    return render(request, 'core/historico_ocorrencias_status.html', {
        'ocorrencias': ocorrencias,
        'sistemas': sistemas,
        'unidades': unidades,
        'status_choices': OcorrenciaSistema.STATUS_CHOICES,
        'impacto_choices': OcorrenciaSistema.IMPACTO_CHOICES,
        'busca': request.GET.get('busca', '').strip(),
        'sistema_id': request.GET.get('sistema', '').strip(),
        'unidade_id': request.GET.get('unidade', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'impacto': request.GET.get('impacto', '').strip(),
        'data_inicio': request.GET.get('data_inicio', '').strip(),
        'data_fim': request.GET.get('data_fim', '').strip(),
        'total_ocorrencias': total_ocorrencias,
        'query_string': request.GET.urlencode(),
    })


@login_required(login_url='/')
def exportar_historico_ocorrencias_csv(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    ocorrencias = filtrar_ocorrencias_historico(request, request.user)

    nome_arquivo = f'historico_ocorrencias_{timezone.localdate().strftime("%Y%m%d")}.csv'

    response = HttpResponse(
        content_type='text/csv; charset=utf-8-sig'
    )
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'

    response.write('\ufeff')

    writer = csv.writer(
        response,
        delimiter=';',
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )

    writer.writerow([
        'ID',
        'Sistema',
        'Unidade',
        'Status',
        'Impacto',
        'Titulo',
        'Mensagem inicial',
        'Previsao',
        'Acao da TI',
        'Causa raiz',
        'Solucao aplicada',
        'Observacao final',
        'Aberto em',
        'Encerrado em',
    ])

    for ocorrencia in ocorrencias:
        writer.writerow([
            ocorrencia.id,
            ocorrencia.sistema.nome if ocorrencia.sistema else '',
            ocorrencia.unidade.nome if ocorrencia.unidade else 'Geral / Todas as unidades',
            ocorrencia.get_status_display(),
            ocorrencia.get_impacto_display(),
            ocorrencia.titulo,
            ocorrencia.mensagem,
            ocorrencia.previsao,
            ocorrencia.acao_ti,
            ocorrencia.causa_raiz,
            ocorrencia.solucao_aplicada,
            ocorrencia.observacao_encerramento,
            formatar_data_hora_csv(ocorrencia.aberto_em),
            formatar_data_hora_csv(ocorrencia.encerrado_em),
        ])

    return response


@login_required(login_url='/')
def nova_ocorrencia_status(request):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    sistemas = SistemaMonitorado.objects.filter(
        ativo=True
    ).order_by(
        'ordem',
        'nome'
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    erro = ''

    if request.method == 'POST':
        sistema_id = request.POST.get('sistema', '').strip()
        unidade_id = request.POST.get('unidade', '').strip()
        status = request.POST.get('status', '').strip()
        impacto = request.POST.get('impacto', '').strip()
        titulo = request.POST.get('titulo', '').strip()
        mensagem = request.POST.get('mensagem', '').strip()
        previsao = request.POST.get('previsao', '').strip()
        acao_ti = request.POST.get('acao_ti', '').strip()

        if not sistema_id or not status or not impacto or not titulo:
            erro = 'Preencha sistema, status, impacto e título.'
        else:
            sistema = get_object_or_404(SistemaMonitorado, id=sistema_id, ativo=True)
            unidade = None

            if unidade_id:
                unidade = get_object_or_404(Unidade, id=unidade_id, ativo=True)

            ocorrencia = OcorrenciaSistema.objects.create(
                sistema=sistema,
                unidade=unidade,
                status=status,
                impacto=impacto,
                titulo=titulo,
                mensagem=mensagem,
                previsao=previsao,
                acao_ti=acao_ti,
                ativo=True,
            )

            registrar_auditoria_status_abertura(request, ocorrencia)

            messages.success(request, 'Ocorrência aberta com sucesso.')
            return redirect('status_sistemas')

    return render(request, 'core/nova_ocorrencia_status.html', {
        'page_title': 'Nova ocorrência de sistema',
        'sistemas': sistemas,
        'unidades': unidades,
        'status_choices': OcorrenciaSistema.STATUS_CHOICES,
        'impacto_choices': OcorrenciaSistema.IMPACTO_CHOICES,
        'erro': erro,
    })


@login_required(login_url='/')
def encerrar_ocorrencia_status(request, ocorrencia_id):
    nome_modulo = 'Status dos Sistemas'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_status(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    ocorrencia = get_object_or_404(
        OcorrenciaSistema.objects.select_related('sistema', 'unidade'),
        id=ocorrencia_id,
        ativo=True
    )

    erro = ''

    if request.method == 'POST':
        causa_raiz = request.POST.get('causa_raiz', '').strip()
        solucao_aplicada = request.POST.get('solucao_aplicada', '').strip()
        observacao_encerramento = request.POST.get('observacao_encerramento', '').strip()

        if not causa_raiz or not solucao_aplicada:
            erro = 'Preencha causa raiz e solução aplicada para encerrar a ocorrência.'
        else:
            ocorrencia.causa_raiz = causa_raiz
            ocorrencia.solucao_aplicada = solucao_aplicada
            ocorrencia.observacao_encerramento = observacao_encerramento
            ocorrencia.ativo = False
            ocorrencia.encerrado_em = timezone.now()
            ocorrencia.save()

            registrar_auditoria_status_encerramento(request, ocorrencia)

            messages.success(request, 'Ocorrência encerrada com sucesso.')
            return redirect('status_sistemas')

    return render(request, 'core/encerrar_ocorrencia_status.html', {
        'ocorrencia': ocorrencia,
        'erro': erro,
    })


@login_required(login_url='/')
def manuais_procedimentos(request):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudos = buscar_manuais_filtrados(request, modulo)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    status = request.GET.get('status', '').strip()

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    tipos_conteudo = ConteudoModulo.TIPO_CHOICES
    pode_gerenciar = usuario_pode_gerenciar_manuais(request.user)

    return render(request, 'core/manuais_procedimentos.html', {
        'modulo': modulo,
        'conteudos': conteudos,
        'unidades': unidades,
        'tipos_conteudo': tipos_conteudo,
        'busca': busca,
        'unidade_id': unidade_id,
        'tipo': tipo,
        'status': status,
        'total_conteudos': conteudos.count(),
        'total_ativos': conteudos.filter(ativo=True).count(),
        'total_inativos': conteudos.filter(ativo=False).count() if pode_gerenciar else 0,
        'total_gerais': conteudos.filter(unidade__isnull=True).count(),
        'total_com_arquivo': conteudos.exclude(arquivo='').filter(arquivo__isnull=False).count(),
        'total_com_link': conteudos.exclude(link_externo='').count(),
        'pode_gerenciar': pode_gerenciar,
    })


@login_required(login_url='/')
def novo_manual_procedimento(request):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    grupos = Group.objects.all().order_by('name')

    form_data = {
        'unidade': '',
        'tipo': 'manual',
        'titulo': '',
        'descricao': '',
        'link_externo': '',
        'ordem': 0,
        'ativo': True,
        'remover_arquivo': False,
        'grupos_permitidos': [],
    }

    if request.method == 'POST':
        form_data = montar_form_data_manual(request)
        arquivo = request.FILES.get('arquivo')

        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do conteúdo.')

        if not form_data['tipo']:
            erros.append('Informe o tipo do conteúdo.')

        if not arquivo and not form_data['link_externo'] and form_data['tipo'] not in ['observacao']:
            erros.append('Informe um arquivo ou um link externo.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_manual_procedimento.html', {
                'titulo': 'Novo manual / procedimento',
                'subtitulo': 'Cadastre um manual, POP, procedimento, link, contingência ou observação.',
                'form_data': form_data,
                'unidades': unidades,
                'grupos': grupos,
                'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
                'url_salvar': '/portal/modulos/manuais-procedimentos/novo/',
                'modo': 'novo',
            })

        conteudo = ConteudoModulo.objects.create(
            modulo=modulo,
            unidade_id=form_data['unidade'] or None,
            tipo=form_data['tipo'],
            titulo=form_data['titulo'],
            descricao=form_data['descricao'],
            arquivo=arquivo,
            link_externo=form_data['link_externo'],
            ordem=ordem,
            ativo=form_data['ativo'],
        )

        if form_data['grupos_permitidos']:
            conteudo.grupos_permitidos.set(form_data['grupos_permitidos'])
        else:
            conteudo.grupos_permitidos.clear()

        registrar_auditoria_manual(
            request=request,
            conteudo=conteudo,
            acao='criado',
            titulo=f'Manual / procedimento criado: {conteudo.titulo}'
        )

        messages.success(request, 'Manual / procedimento cadastrado com sucesso.')
        return redirect('/portal/modulos/manuais-procedimentos/')

    return render(request, 'core/formulario_manual_procedimento.html', {
        'titulo': 'Novo manual / procedimento',
        'subtitulo': 'Cadastre um manual, POP, procedimento, link, contingência ou observação.',
        'form_data': form_data,
        'unidades': unidades,
        'grupos': grupos,
        'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
        'url_salvar': '/portal/modulos/manuais-procedimentos/novo/',
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_manual_procedimento(request, conteudo_id):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudo = get_object_or_404(
        ConteudoModulo.objects.prefetch_related('grupos_permitidos'),
        id=conteudo_id,
        modulo=modulo
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    grupos = Group.objects.all().order_by('name')
    form_data = manual_para_form_data(conteudo)

    if request.method == 'POST':
        form_data = montar_form_data_manual(request)
        arquivo = request.FILES.get('arquivo')

        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do conteúdo.')

        if not form_data['tipo']:
            erros.append('Informe o tipo do conteúdo.')

        arquivo_atual_sera_removido = form_data['remover_arquivo']
        tem_arquivo_final = bool(arquivo) or (bool(conteudo.arquivo) and not arquivo_atual_sera_removido)

        if not tem_arquivo_final and not form_data['link_externo'] and form_data['tipo'] not in ['observacao']:
            erros.append('Informe um arquivo ou um link externo.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_manual_procedimento.html', {
                'titulo': 'Editar manual / procedimento',
                'subtitulo': 'Atualize os dados do conteúdo selecionado.',
                'form_data': form_data,
                'conteudo_editado': conteudo,
                'unidades': unidades,
                'grupos': grupos,
                'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
                'url_salvar': f'/portal/modulos/manuais-procedimentos/editar/{conteudo.id}/',
                'modo': 'editar',
            })

        conteudo.unidade_id = form_data['unidade'] or None
        conteudo.tipo = form_data['tipo']
        conteudo.titulo = form_data['titulo']
        conteudo.descricao = form_data['descricao']
        conteudo.link_externo = form_data['link_externo']
        conteudo.ordem = ordem
        conteudo.ativo = form_data['ativo']

        if form_data['remover_arquivo']:
            conteudo.arquivo = None

        if arquivo:
            conteudo.arquivo = arquivo

        conteudo.save()

        if form_data['grupos_permitidos']:
            conteudo.grupos_permitidos.set(form_data['grupos_permitidos'])
        else:
            conteudo.grupos_permitidos.clear()

        registrar_auditoria_manual(
            request=request,
            conteudo=conteudo,
            acao='alterado',
            titulo=f'Manual / procedimento alterado: {conteudo.titulo}'
        )

        messages.success(request, 'Manual / procedimento atualizado com sucesso.')
        return redirect('/portal/modulos/manuais-procedimentos/')

    return render(request, 'core/formulario_manual_procedimento.html', {
        'titulo': 'Editar manual / procedimento',
        'subtitulo': 'Atualize os dados do conteúdo selecionado.',
        'form_data': form_data,
        'conteudo_editado': conteudo,
        'unidades': unidades,
        'grupos': grupos,
        'tipos_conteudo': ConteudoModulo.TIPO_CHOICES,
        'url_salvar': f'/portal/modulos/manuais-procedimentos/editar/{conteudo.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_manual_procedimento(request, conteudo_id):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudo = get_object_or_404(
        ConteudoModulo,
        id=conteudo_id,
        modulo=modulo
    )

    conteudo.ativo = False
    conteudo.save()

    registrar_auditoria_manual(
        request=request,
        conteudo=conteudo,
        acao='alterado',
        titulo=f'Manual / procedimento inativado: {conteudo.titulo}'
    )

    messages.success(request, 'Manual / procedimento inativado com sucesso.')
    return redirect('/portal/modulos/manuais-procedimentos/')


@login_required(login_url='/')
def reativar_manual_procedimento(request, conteudo_id):
    nome_modulo = 'Manuais e Procedimentos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_manuais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    conteudo = get_object_or_404(
        ConteudoModulo,
        id=conteudo_id,
        modulo=modulo
    )

    conteudo.ativo = True
    conteudo.save()

    registrar_auditoria_manual(
        request=request,
        conteudo=conteudo,
        acao='alterado',
        titulo=f'Manual / procedimento reativado: {conteudo.titulo}'
    )

    messages.success(request, 'Manual / procedimento reativado com sucesso.')
    return redirect('/portal/modulos/manuais-procedimentos/')


@login_required(login_url='/')
def links_uteis(request):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)
    links = buscar_links_uteis_filtrados(request, modulo)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    status = request.GET.get('status', '').strip()

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    pode_gerenciar = usuario_pode_gerenciar_links_uteis(request.user)

    return render(request, 'core/links_uteis.html', {
        'modulo': modulo,
        'links': links,
        'unidades': unidades,
        'busca': busca,
        'unidade_id': unidade_id,
        'status': status,
        'total_links': links.count(),
        'total_ativos': links.filter(ativo=True).count(),
        'total_inativos': links.filter(ativo=False).count() if pode_gerenciar else 0,
        'total_gerais': links.filter(unidade__isnull=True).count(),
        'total_unidade': links.filter(unidade__isnull=False).count(),
        'pode_gerenciar': pode_gerenciar,
    })


@login_required(login_url='/')
def novo_link_util(request):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    form_data = {
        'unidade': '',
        'titulo': '',
        'descricao': '',
        'link_externo': '',
        'ordem': 0,
        'ativo': True,
    }

    if request.method == 'POST':
        form_data = montar_form_data_link_util(request)
        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do link.')

        if not form_data['link_externo']:
            erros.append('Informe o endereço do link.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_link_util.html', {
                'titulo': 'Novo link útil',
                'subtitulo': 'Cadastre um novo sistema, portal ou atalho interno.',
                'form_data': form_data,
                'unidades': unidades,
                'url_salvar': '/portal/modulos/links-uteis/novo/',
                'modo': 'novo',
            })

        link = ConteudoModulo.objects.create(
            modulo=modulo,
            unidade_id=form_data['unidade'] or None,
            tipo='link',
            titulo=form_data['titulo'],
            descricao=form_data['descricao'],
            link_externo=form_data['link_externo'],
            ordem=ordem,
            ativo=form_data['ativo'],
        )

        registrar_auditoria_link_util(
            request=request,
            link=link,
            acao='criado',
            titulo=f'Link útil criado: {link.titulo}'
        )

        messages.success(request, 'Link útil cadastrado com sucesso.')
        return redirect('/portal/modulos/links-uteis/')

    return render(request, 'core/formulario_link_util.html', {
        'titulo': 'Novo link útil',
        'subtitulo': 'Cadastre um novo sistema, portal ou atalho interno.',
        'form_data': form_data,
        'unidades': unidades,
        'url_salvar': '/portal/modulos/links-uteis/novo/',
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_link_util(request, link_id):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    link = get_object_or_404(
        ConteudoModulo,
        id=link_id,
        modulo=modulo,
        tipo='link'
    )

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    form_data = link_util_para_form_data(link)

    if request.method == 'POST':
        form_data = montar_form_data_link_util(request)
        erros = []

        if not form_data['titulo']:
            erros.append('Informe o título do link.')

        if not form_data['link_externo']:
            erros.append('Informe o endereço do link.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'core/formulario_link_util.html', {
                'titulo': 'Editar link útil',
                'subtitulo': 'Atualize os dados do link selecionado.',
                'form_data': form_data,
                'link_editado': link,
                'unidades': unidades,
                'url_salvar': f'/portal/modulos/links-uteis/editar/{link.id}/',
                'modo': 'editar',
            })

        link.unidade_id = form_data['unidade'] or None
        link.titulo = form_data['titulo']
        link.descricao = form_data['descricao']
        link.link_externo = form_data['link_externo']
        link.ordem = ordem
        link.ativo = form_data['ativo']
        link.save()

        registrar_auditoria_link_util(
            request=request,
            link=link,
            acao='alterado',
            titulo=f'Link útil alterado: {link.titulo}'
        )

        messages.success(request, 'Link útil atualizado com sucesso.')
        return redirect('/portal/modulos/links-uteis/')

    return render(request, 'core/formulario_link_util.html', {
        'titulo': 'Editar link útil',
        'subtitulo': 'Atualize os dados do link selecionado.',
        'form_data': form_data,
        'link_editado': link,
        'unidades': unidades,
        'url_salvar': f'/portal/modulos/links-uteis/editar/{link.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_link_util(request, link_id):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    link = get_object_or_404(
        ConteudoModulo,
        id=link_id,
        modulo=modulo,
        tipo='link'
    )

    link.ativo = False
    link.save()

    registrar_auditoria_link_util(
        request=request,
        link=link,
        acao='alterado',
        titulo=f'Link útil inativado: {link.titulo}'
    )

    messages.success(request, 'Link útil inativado com sucesso.')
    return redirect('/portal/modulos/links-uteis/')


@login_required(login_url='/')
def reativar_link_util(request, link_id):
    nome_modulo = 'Links Úteis / Sistemas Internos'

    if not usuario_pode_acessar_modulo(request.user, nome_modulo):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_links_uteis(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    modulo = Modulo.objects.get(nome=nome_modulo, ativo=True)

    link = get_object_or_404(
        ConteudoModulo,
        id=link_id,
        modulo=modulo,
        tipo='link'
    )

    link.ativo = True
    link.save()

    registrar_auditoria_link_util(
        request=request,
        link=link,
        acao='alterado',
        titulo=f'Link útil reativado: {link.titulo}'
    )

    messages.success(request, 'Link útil reativado com sucesso.')
    return redirect('/portal/modulos/links-uteis/')


@require_POST
def login_intranet(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'ok': False,
            'message': 'Requisição inválida.'
        }, status=400)

    unidade_sigla = data.get('unidade', '').strip()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if not unidade_sigla or not username or not password:
        return JsonResponse({
            'ok': False,
            'message': 'Preencha unidade, usuário e senha.'
        }, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse({
            'ok': False,
            'message': 'Usuário ou senha inválidos.'
        }, status=401)

    if not user.is_active:
        return JsonResponse({
            'ok': False,
            'message': 'Usuário inativo. Procure a Tecnologia da Informação.'
        }, status=403)

    if not obter_unidade_usuario(user):
        return JsonResponse({
            'ok': False,
            'message': 'Usuário sem unidade vinculada. Procure a Tecnologia da Informação.'
        }, status=403)

    if user.unidade.sigla != unidade_sigla:
        return JsonResponse({
            'ok': False,
            'message': 'A unidade selecionada não corresponde ao cadastro do usuário.'
        }, status=403)

    login(request, user)

    grupos = list(user.groups.values_list('name', flat=True))

    return JsonResponse({
        'ok': True,
        'message': 'Login realizado com sucesso.',
        'redirect_url': '/portal/',
        'user': {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'unidade': user.unidade.nome if user.unidade else '',
            'unidade_sigla': user.unidade.sigla if user.unidade else '',
            'setor': user.setor.nome if user.setor else '',
            'tipo_prestador': user.tipo_prestador,
            'primeiro_acesso': user.primeiro_acesso,
            'grupos': grupos,
        }
    })


@require_POST
def logout_intranet(request):
    logout(request)

    return JsonResponse({
        'ok': True,
        'message': 'Logout realizado com sucesso.',
        'redirect_url': '/'
    })


