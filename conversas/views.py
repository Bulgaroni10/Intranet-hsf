from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import ConversaChat, MensagemChat


def usuario_nome(usuario):
    nome = usuario.get_full_name()

    if nome:
        return nome

    return usuario.username


def usuario_descricao(usuario):
    partes = []

    if getattr(usuario, 'setor', None):
        partes.append(usuario.setor.nome)

    if getattr(usuario, 'unidade', None):
        partes.append(usuario.unidade.sigla)

    if partes:
        return ' • '.join(partes)

    return usuario.email or usuario.username


def usuario_para_json(usuario):
    return {
        'id': usuario.id,
        'nome': usuario_nome(usuario),
        'username': usuario.username,
        'descricao': usuario_descricao(usuario),
        'email': usuario.email or '',
        'unidade': usuario.unidade.sigla if getattr(usuario, 'unidade', None) else '',
        'setor': usuario.setor.nome if getattr(usuario, 'setor', None) else '',
    }


def contar_conversas_nao_lidas(usuario):
    if not usuario.is_authenticated:
        return 0

    return MensagemChat.objects.filter(
        conversa__ativo=True,
        conversa__participantes=usuario,
    ).exclude(
        remetente=usuario
    ).exclude(
        lida_por=usuario
    ).values(
        'conversa_id'
    ).distinct().count()


def mensagem_foi_lida_por_destinatarios(mensagem):
    total_destinatarios = mensagem.conversa.participantes.exclude(
        id=mensagem.remetente_id
    ).count()

    if total_destinatarios <= 0:
        return True

    total_leitores = mensagem.lida_por.exclude(
        id=mensagem.remetente_id
    ).count()

    return total_leitores >= total_destinatarios


def nomes_leitores_mensagem(mensagem):
    leitores = mensagem.lida_por.exclude(
        id=mensagem.remetente_id
    ).order_by(
        'first_name',
        'last_name',
        'username'
    )

    nomes = []

    for leitor in leitores:
        nomes.append(usuario_nome(leitor))

    return nomes


def mensagem_para_json(mensagem, usuario_logado):
    minha = mensagem.remetente_id == usuario_logado.id
    lida_destinatarios = mensagem_foi_lida_por_destinatarios(mensagem)

    status_leitura = ''

    if minha:
        if lida_destinatarios:
            status_leitura = 'Visto'
        else:
            status_leitura = 'Enviado'

    return {
        'id': mensagem.id,
        'texto': mensagem.texto,
        'criado_em': timezone.localtime(mensagem.criado_em).strftime('%d/%m/%Y %H:%M'),
        'hora': timezone.localtime(mensagem.criado_em).strftime('%H:%M'),
        'minha': minha,
        'lida_destinatarios': lida_destinatarios,
        'status_leitura': status_leitura,
        'lida_por_nomes': nomes_leitores_mensagem(mensagem),
        'remetente': {
            'id': mensagem.remetente.id,
            'nome': usuario_nome(mensagem.remetente),
            'username': mensagem.remetente.username,
        },
    }


def conversa_titulo_descricao(conversa, usuario_logado):
    participantes = list(
        conversa.participantes.exclude(
            id=usuario_logado.id
        ).order_by(
            'first_name',
            'last_name',
            'username'
        )
    )

    if conversa.tipo == 'grupo':
        nome = conversa.nome_grupo or f'Grupo #{conversa.id}'
        descricao = f'{conversa.participantes.count()} participantes'

        nomes = [usuario_nome(usuario) for usuario in participantes[:4]]

        if nomes:
            descricao = f'{descricao} • ' + ', '.join(nomes)

        return {
            'id': None,
            'nome': nome,
            'username': nome,
            'descricao': descricao,
            'email': '',
            'unidade': '',
            'setor': '',
        }

    outro_usuario = participantes[0] if participantes else usuario_logado

    return usuario_para_json(outro_usuario)


def conversa_para_json(conversa, usuario_logado):
    ultima_mensagem = conversa.mensagens.order_by('-criado_em').first()
    usuario_json = conversa_titulo_descricao(conversa, usuario_logado)

    nao_lidas = conversa.mensagens.exclude(
        remetente=usuario_logado
    ).exclude(
        lida_por=usuario_logado
    ).count()

    pode_gerenciar_grupo = False

    if conversa.tipo == 'grupo':
        if conversa.criado_por_id == usuario_logado.id or usuario_logado.is_superuser:
            pode_gerenciar_grupo = True

    return {
        'id': conversa.id,
        'tipo': conversa.tipo,
        'nome': usuario_json['nome'],
        'descricao': usuario_json['descricao'],
        'usuario': usuario_json,
        'ultima_mensagem': ultima_mensagem.texto if ultima_mensagem else '',
        'ultima_mensagem_hora': timezone.localtime(ultima_mensagem.criado_em).strftime('%H:%M') if ultima_mensagem else '',
        'nao_lidas': nao_lidas,
        'atualizado_em': timezone.localtime(conversa.atualizado_em).strftime('%d/%m/%Y %H:%M'),
        'pode_gerenciar_grupo': pode_gerenciar_grupo,
    }


@login_required(login_url='/login/')
def conversas_home(request):
    User = get_user_model()

    usuarios = User.objects.filter(
        is_active=True
    ).exclude(
        id=request.user.id
    ).select_related(
        'unidade',
        'setor'
    ).order_by(
        'first_name',
        'last_name',
        'username'
    )

    return render(request, 'conversas/conversas_home.html', {
        'usuarios': usuarios,
        'abrir_conversa_id': request.GET.get('conversa_id', '').strip(),
    })


@login_required(login_url='/login/')
@require_GET
def contador_mensagens_nao_lidas(request):
    total = contar_conversas_nao_lidas(request.user)

    return JsonResponse({
        'ok': True,
        'total': total,
    })


@login_required(login_url='/login/')
@require_GET
def api_listar_conversas(request):
    conversas = ConversaChat.objects.filter(
        ativo=True,
        participantes=request.user
    ).prefetch_related(
        'participantes',
        'mensagens',
        'mensagens__remetente',
        'mensagens__lida_por',
    ).order_by(
        '-atualizado_em'
    )

    dados = []

    for conversa in conversas:
        dados.append(conversa_para_json(conversa, request.user))

    return JsonResponse({
        'ok': True,
        'conversas': dados,
        'total_nao_lidas': contar_conversas_nao_lidas(request.user),
    })


@login_required(login_url='/login/')
@require_POST
def api_iniciar_conversa(request):
    usuario_id = request.POST.get('usuario_id')

    if not usuario_id:
        return JsonResponse({
            'ok': False,
            'message': 'Usuário não informado.'
        }, status=400)

    User = get_user_model()

    usuario_destino = get_object_or_404(
        User.objects.filter(is_active=True),
        id=usuario_id
    )

    if usuario_destino.id == request.user.id:
        return JsonResponse({
            'ok': False,
            'message': 'Você não pode iniciar conversa com você mesmo.'
        }, status=400)

    conversa = ConversaChat.objects.filter(
        ativo=True,
        tipo='individual',
        participantes=request.user
    ).filter(
        participantes=usuario_destino
    ).distinct().first()

    if not conversa:
        conversa = ConversaChat.objects.create(
            tipo='individual',
            ativo=True,
            criado_por=request.user,
        )

        conversa.participantes.add(request.user)
        conversa.participantes.add(usuario_destino)

    return JsonResponse({
        'ok': True,
        'conversa': conversa_para_json(conversa, request.user),
    })


@login_required(login_url='/login/')
@require_POST
def api_criar_grupo(request):
    nome_grupo = request.POST.get('nome_grupo', '').strip()

    usuarios_ids = request.POST.getlist('usuarios_ids')

    if not usuarios_ids:
        usuarios_ids = request.POST.getlist('usuarios_ids[]')

    if not nome_grupo:
        return JsonResponse({
            'ok': False,
            'message': 'Informe o nome do grupo.'
        }, status=400)

    ids_limpos = []

    for usuario_id in usuarios_ids:
        try:
            usuario_id_int = int(usuario_id)

            if usuario_id_int != request.user.id:
                ids_limpos.append(usuario_id_int)

        except (TypeError, ValueError):
            pass

    ids_limpos = list(set(ids_limpos))

    if len(ids_limpos) < 1:
        return JsonResponse({
            'ok': False,
            'message': 'Selecione pelo menos um participante além de você.'
        }, status=400)

    User = get_user_model()

    participantes = list(
        User.objects.filter(
            is_active=True,
            id__in=ids_limpos
        ).exclude(
            id=request.user.id
        )
    )

    if not participantes:
        return JsonResponse({
            'ok': False,
            'message': 'Nenhum participante válido selecionado.'
        }, status=400)

    conversa = ConversaChat.objects.create(
        tipo='grupo',
        nome_grupo=nome_grupo,
        criado_por=request.user,
        ativo=True,
    )

    conversa.participantes.add(request.user)

    for participante in participantes:
        conversa.participantes.add(participante)

    mensagem = MensagemChat.objects.create(
        conversa=conversa,
        remetente=request.user,
        texto=f'Grupo "{nome_grupo}" criado.'
    )

    mensagem.lida_por.add(request.user)

    return JsonResponse({
        'ok': True,
        'message': 'Grupo criado com sucesso.',
        'conversa': conversa_para_json(conversa, request.user),
    })


@login_required(login_url='/login/')
@require_GET
def api_detalhe_grupo(request, conversa_id):
    conversa = get_object_or_404(
        ConversaChat.objects.filter(
            ativo=True,
            tipo='grupo',
            participantes=request.user
        ).prefetch_related(
            'participantes'
        ),
        id=conversa_id
    )

    pode_gerenciar = conversa.criado_por_id == request.user.id or request.user.is_superuser

    participantes = []

    for participante in conversa.participantes.select_related('unidade', 'setor').order_by('first_name', 'last_name', 'username'):
        participantes.append(usuario_para_json(participante))

    return JsonResponse({
        'ok': True,
        'grupo': {
            'id': conversa.id,
            'nome_grupo': conversa.nome_grupo,
            'criado_por_id': conversa.criado_por_id,
            'pode_gerenciar': pode_gerenciar,
            'participantes': participantes,
        }
    })


@login_required(login_url='/login/')
@require_POST
def api_atualizar_grupo(request):
    conversa_id = request.POST.get('conversa_id')
    nome_grupo = request.POST.get('nome_grupo', '').strip()

    usuarios_ids = request.POST.getlist('usuarios_ids')

    if not usuarios_ids:
        usuarios_ids = request.POST.getlist('usuarios_ids[]')

    if not conversa_id:
        return JsonResponse({
            'ok': False,
            'message': 'Grupo não informado.'
        }, status=400)

    if not nome_grupo:
        return JsonResponse({
            'ok': False,
            'message': 'Informe o nome do grupo.'
        }, status=400)

    conversa = get_object_or_404(
        ConversaChat.objects.filter(
            ativo=True,
            tipo='grupo',
            participantes=request.user
        ),
        id=conversa_id
    )

    if conversa.criado_por_id != request.user.id and not request.user.is_superuser:
        return JsonResponse({
            'ok': False,
            'message': 'Você não tem permissão para editar este grupo.'
        }, status=403)

    ids_limpos = []

    for usuario_id in usuarios_ids:
        try:
            usuario_id_int = int(usuario_id)

            if usuario_id_int != request.user.id:
                ids_limpos.append(usuario_id_int)

        except (TypeError, ValueError):
            pass

    ids_limpos = list(set(ids_limpos))

    if len(ids_limpos) < 1:
        return JsonResponse({
            'ok': False,
            'message': 'O grupo precisa ter pelo menos um participante além de você.'
        }, status=400)

    User = get_user_model()

    participantes = list(
        User.objects.filter(
            is_active=True,
            id__in=ids_limpos
        ).exclude(
            id=request.user.id
        )
    )

    if not participantes:
        return JsonResponse({
            'ok': False,
            'message': 'Nenhum participante válido selecionado.'
        }, status=400)

    nome_anterior = conversa.nome_grupo
    participantes_anteriores_ids = set(conversa.participantes.values_list('id', flat=True))

    conversa.nome_grupo = nome_grupo
    conversa.atualizado_em = timezone.now()
    conversa.save()

    conversa.participantes.clear()
    conversa.participantes.add(request.user)

    for participante in participantes:
        conversa.participantes.add(participante)

    participantes_novos_ids = set(conversa.participantes.values_list('id', flat=True))

    mensagens_sistema = []

    if nome_anterior != nome_grupo:
        mensagens_sistema.append(f'Nome do grupo alterado de "{nome_anterior}" para "{nome_grupo}".')

    adicionados = participantes_novos_ids - participantes_anteriores_ids
    removidos = participantes_anteriores_ids - participantes_novos_ids

    if adicionados:
        nomes_adicionados = []
        for usuario in User.objects.filter(id__in=adicionados).order_by('first_name', 'last_name', 'username'):
            nomes_adicionados.append(usuario_nome(usuario))

        mensagens_sistema.append('Participantes adicionados: ' + ', '.join(nomes_adicionados) + '.')

    if removidos:
        nomes_removidos = []
        for usuario in User.objects.filter(id__in=removidos).order_by('first_name', 'last_name', 'username'):
            nomes_removidos.append(usuario_nome(usuario))

        mensagens_sistema.append('Participantes removidos: ' + ', '.join(nomes_removidos) + '.')

    if mensagens_sistema:
        mensagem = MensagemChat.objects.create(
            conversa=conversa,
            remetente=request.user,
            texto='\n'.join(mensagens_sistema)
        )

        mensagem.lida_por.add(request.user)

    return JsonResponse({
        'ok': True,
        'message': 'Grupo atualizado com sucesso.',
        'conversa': conversa_para_json(conversa, request.user),
    })


@login_required(login_url='/login/')
@require_POST
def api_sair_grupo(request):
    conversa_id = request.POST.get('conversa_id')

    if not conversa_id:
        return JsonResponse({
            'ok': False,
            'message': 'Grupo não informado.'
        }, status=400)

    conversa = get_object_or_404(
        ConversaChat.objects.filter(
            ativo=True,
            tipo='grupo',
            participantes=request.user
        ),
        id=conversa_id
    )

    nome_usuario = usuario_nome(request.user)

    conversa.participantes.remove(request.user)

    participantes_restantes = conversa.participantes.all().order_by('id')

    if not participantes_restantes.exists():
        conversa.ativo = False
        conversa.atualizado_em = timezone.now()
        conversa.save()

        return JsonResponse({
            'ok': True,
            'message': 'Você saiu do grupo.',
            'grupo_encerrado': True,
        })

    if conversa.criado_por_id == request.user.id:
        novo_criador = participantes_restantes.first()
        conversa.criado_por = novo_criador

    conversa.atualizado_em = timezone.now()
    conversa.save()

    mensagem = MensagemChat.objects.create(
        conversa=conversa,
        remetente=participantes_restantes.first(),
        texto=f'{nome_usuario} saiu do grupo.'
    )

    mensagem.lida_por.add(participantes_restantes.first())

    return JsonResponse({
        'ok': True,
        'message': 'Você saiu do grupo.',
        'grupo_encerrado': False,
    })


@login_required(login_url='/login/')
@require_GET
def api_mensagens_conversa(request, conversa_id):
    conversa = get_object_or_404(
        ConversaChat.objects.filter(
            ativo=True,
            participantes=request.user
        ).prefetch_related(
            'participantes',
            'mensagens',
            'mensagens__remetente',
            'mensagens__lida_por',
        ),
        id=conversa_id
    )

    mensagens_nao_lidas = conversa.mensagens.exclude(
        remetente=request.user
    ).exclude(
        lida_por=request.user
    )

    for mensagem in mensagens_nao_lidas:
        mensagem.lida_por.add(request.user)

    mensagens = conversa.mensagens.select_related(
        'remetente'
    ).prefetch_related(
        'lida_por',
        'conversa__participantes'
    ).order_by(
        'criado_em'
    )

    return JsonResponse({
        'ok': True,
        'conversa': conversa_para_json(conversa, request.user),
        'mensagens': [
            mensagem_para_json(mensagem, request.user)
            for mensagem in mensagens
        ],
        'total_nao_lidas': contar_conversas_nao_lidas(request.user),
    })


@login_required(login_url='/login/')
@require_POST
def api_enviar_mensagem(request):
    conversa_id = request.POST.get('conversa_id')
    texto = request.POST.get('texto', '').strip()

    if not conversa_id:
        return JsonResponse({
            'ok': False,
            'message': 'Conversa não informada.'
        }, status=400)

    if not texto:
        return JsonResponse({
            'ok': False,
            'message': 'Digite uma mensagem antes de enviar.'
        }, status=400)

    conversa = get_object_or_404(
        ConversaChat.objects.filter(
            ativo=True,
            participantes=request.user
        ),
        id=conversa_id
    )

    mensagem = MensagemChat.objects.create(
        conversa=conversa,
        remetente=request.user,
        texto=texto
    )

    mensagem.lida_por.add(request.user)

    return JsonResponse({
        'ok': True,
        'mensagem': mensagem_para_json(mensagem, request.user),
        'conversa': conversa_para_json(conversa, request.user),
    })