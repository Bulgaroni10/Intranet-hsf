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

try:
    from inventario_ti.models import ComputadorInventario
except Exception:
    ComputadorInventario = None




PERFIS_TI = ('TI Administrador', 'TI Suporte', 'TI')
PERFIS_GESTAO = ('Gestão', 'Gerência', 'Diretoria', 'Responsável Técnico')


def usuario_pertence_a_algum_grupo(user, nomes_grupos):
    if not user or not user.is_authenticated:
        return False

    return user.groups.filter(name__in=nomes_grupos).exists()


def usuario_eh_admin_ti(user):
    if not user or not user.is_authenticated:
        return False

    return user.is_superuser or usuario_pertence_a_algum_grupo(user, ('TI Administrador',))


def usuario_eh_ti(user):
    return usuario_eh_admin_ti(user) or usuario_pertence_a_algum_grupo(user, PERFIS_TI)


def usuario_eh_gestao(user):
    return usuario_pertence_a_algum_grupo(user, PERFIS_GESTAO)


def usuario_pode_ver_painel_tecnico(user):
    return usuario_eh_ti(user)


def usuario_pode_acessar_modulo(user, nome_modulo):
    if usuario_eh_admin_ti(user):
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
    if usuario_eh_admin_ti(user):
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
    return usuario_eh_admin_ti(user)


def usuario_pode_acessar_inventario_ti(user):
    return usuario_eh_ti(user)


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

    if not usuario_eh_ti(user):
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

    if not usuario_eh_ti(user):
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


def buscar_resumo_inventario_ti():
    if ComputadorInventario is None:
        return {
            'total_computadores': 0,
            'total_computadores_online': 0,
            'total_computadores_offline': 0,
            'total_computadores_sem_patrimonio': 0,
            'ultimos_computadores': [],
        }

    try:
        computadores = list(ComputadorInventario.objects.all())
    except Exception:
        return {
            'total_computadores': 0,
            'total_computadores_online': 0,
            'total_computadores_offline': 0,
            'total_computadores_sem_patrimonio': 0,
            'ultimos_computadores': [],
        }

    total = len(computadores)
    online = len([pc for pc in computadores if pc.online])
    offline = total - online
    sem_patrimonio = len([
        pc for pc in computadores
        if not pc.patrimonio or pc.patrimonio == '-'
    ])

    return {
        'total_computadores': total,
        'total_computadores_online': online,
        'total_computadores_offline': offline,
        'total_computadores_sem_patrimonio': sem_patrimonio,
        'ultimos_computadores': ComputadorInventario.objects.order_by('-ultimo_contato')[:6],
    }
