from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.models import RegistroAuditoria
from modulos.models import Modulo
from usuarios.models import Unidade
from .models import RamalContato


NOME_MODULO_RAMAIS = 'Ramais e Contatos'


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


def usuario_pode_gerenciar_ramais(user):
    return user.is_superuser or user.groups.filter(name='TI Administrador').exists()


def obter_ip_cliente(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def registrar_auditoria_ramal(request, contato, acao, titulo):
    RegistroAuditoria.objects.create(
        modulo='ramais',
        acao=acao,
        titulo=titulo,
        descricao=(
            f'Contato: {contato.nome}\n'
            f'Tipo: {contato.get_tipo_display()}\n'
            f'Unidade: {contato.unidade.nome if contato.unidade else "Geral / Todas as unidades"}\n'
            f'Setor: {contato.setor or "Não informado"}\n'
            f'Cargo / função: {contato.cargo_funcao or "Não informado"}\n'
            f'Ramal: {contato.ramal or "Não informado"}\n'
            f'Telefone: {contato.telefone or "Não informado"}\n'
            f'Celular: {contato.celular or "Não informado"}\n'
            f'WhatsApp: {contato.whatsapp or "Não informado"}\n'
            f'E-mail: {contato.email or "Não informado"}\n'
            f'Localização: {contato.localizacao or "Não informada"}\n'
            f'Ativo: {"Sim" if contato.ativo else "Não"}'
        ),
        modelo='RamalContato',
        objeto_id=str(contato.id),
        usuario=request.user,
        unidade=contato.unidade,
        ip_origem=obter_ip_cliente(request),
    )


def montar_form_data_contato(request):
    return {
        'unidade': request.POST.get('unidade', '').strip(),
        'tipo': request.POST.get('tipo', 'setor').strip(),
        'setor': request.POST.get('setor', '').strip(),
        'nome': request.POST.get('nome', '').strip(),
        'cargo_funcao': request.POST.get('cargo_funcao', '').strip(),
        'ramal': request.POST.get('ramal', '').strip(),
        'telefone': request.POST.get('telefone', '').strip(),
        'celular': request.POST.get('celular', '').strip(),
        'whatsapp': request.POST.get('whatsapp', '').strip(),
        'email': request.POST.get('email', '').strip().lower(),
        'localizacao': request.POST.get('localizacao', '').strip(),
        'observacao': request.POST.get('observacao', '').strip(),
        'ativo': request.POST.get('ativo') == 'on',
        'ordem': request.POST.get('ordem', '0').strip(),
    }


def contato_para_form_data(contato):
    return {
        'unidade': str(contato.unidade_id) if contato.unidade_id else '',
        'tipo': contato.tipo,
        'setor': contato.setor,
        'nome': contato.nome,
        'cargo_funcao': contato.cargo_funcao,
        'ramal': contato.ramal,
        'telefone': contato.telefone,
        'celular': contato.celular,
        'whatsapp': contato.whatsapp,
        'email': contato.email,
        'localizacao': contato.localizacao,
        'observacao': contato.observacao,
        'ativo': contato.ativo,
        'ordem': contato.ordem,
    }


def tratar_erros_validacao(erro):
    mensagens = []

    if hasattr(erro, 'message_dict'):
        for campo, mensagens_campo in erro.message_dict.items():
            for mensagem in mensagens_campo:
                mensagens.append(mensagem)
    else:
        for mensagem in erro.messages:
            mensagens.append(mensagem)

    return mensagens


def buscar_contatos_visiveis(request):
    pode_gerenciar = usuario_pode_gerenciar_ramais(request.user)

    contatos = RamalContato.objects.select_related(
        'unidade'
    )

    if not pode_gerenciar:
        contatos = contatos.filter(
            ativo=True
        ).filter(
            Q(unidade=request.user.unidade) |
            Q(unidade__isnull=True)
        )

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    setor = request.GET.get('setor', '').strip()
    status = request.GET.get('status', '').strip()

    if busca:
        contatos = contatos.filter(
            Q(nome__icontains=busca) |
            Q(setor__icontains=busca) |
            Q(cargo_funcao__icontains=busca) |
            Q(ramal__icontains=busca) |
            Q(telefone__icontains=busca) |
            Q(celular__icontains=busca) |
            Q(whatsapp__icontains=busca) |
            Q(email__icontains=busca) |
            Q(localizacao__icontains=busca) |
            Q(observacao__icontains=busca) |
            Q(unidade__nome__icontains=busca) |
            Q(unidade__sigla__icontains=busca)
        )

    if unidade_id:
        if unidade_id == 'geral':
            contatos = contatos.filter(unidade__isnull=True)
        else:
            contatos = contatos.filter(unidade_id=unidade_id)

    if tipo:
        contatos = contatos.filter(tipo=tipo)

    if setor:
        contatos = contatos.filter(setor__iexact=setor)

    if pode_gerenciar:
        if status == 'ativo':
            contatos = contatos.filter(ativo=True)
        elif status == 'inativo':
            contatos = contatos.filter(ativo=False)

    return contatos.order_by(
        'unidade__nome',
        'setor',
        'ordem',
        'nome'
    )


@login_required(login_url='/')
def ramais_contatos(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_RAMAIS):
        return render(request, 'core/sem_permissao.html', status=403)

    pode_gerenciar = usuario_pode_gerenciar_ramais(request.user)

    contatos = buscar_contatos_visiveis(request)

    busca = request.GET.get('busca', '').strip()
    unidade_id = request.GET.get('unidade', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    setor = request.GET.get('setor', '').strip()
    status = request.GET.get('status', '').strip()

    unidades = Unidade.objects.filter(
        ativo=True
    ).order_by(
        'nome'
    )

    setores = RamalContato.objects.filter(
        ativo=True
    ).exclude(
        setor=''
    ).values_list(
        'setor',
        flat=True
    ).distinct().order_by(
        'setor'
    )

    total_contatos = contatos.count()
    total_ativos = contatos.filter(ativo=True).count()
    total_inativos = contatos.filter(ativo=False).count() if pode_gerenciar else 0
    total_gerais = contatos.filter(unidade__isnull=True).count()
    total_emergencia = contatos.filter(tipo='emergencia').count()

    return render(request, 'ramais_contatos/ramais_contatos.html', {
        'contatos': contatos,
        'unidades': unidades,
        'setores': setores,
        'tipos': RamalContato.TIPO_CHOICES,
        'busca': busca,
        'unidade_id': unidade_id,
        'tipo': tipo,
        'setor': setor,
        'status': status,
        'total_contatos': total_contatos,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'total_gerais': total_gerais,
        'total_emergencia': total_emergencia,
        'pode_gerenciar': pode_gerenciar,
    })


@login_required(login_url='/')
def novo_ramal_contato(request):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_RAMAIS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_ramais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    unidades = Unidade.objects.filter(ativo=True).order_by('nome')

    form_data = {
        'unidade': '',
        'tipo': 'setor',
        'setor': '',
        'nome': '',
        'cargo_funcao': '',
        'ramal': '',
        'telefone': '',
        'celular': '',
        'whatsapp': '',
        'email': '',
        'localizacao': '',
        'observacao': '',
        'ativo': True,
        'ordem': 0,
    }

    if request.method == 'POST':
        form_data = montar_form_data_contato(request)

        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do contato, setor ou serviço.')

        if not form_data['tipo']:
            erros.append('Informe o tipo do contato.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'ramais_contatos/formulario_ramal_contato.html', {
                'titulo': 'Novo ramal / contato',
                'subtitulo': 'Cadastre um novo ramal, contato interno, setor ou serviço.',
                'form_data': form_data,
                'unidades': unidades,
                'tipos': RamalContato.TIPO_CHOICES,
                'url_salvar': '/portal/modulos/ramais-contatos/novo/',
                'modo': 'novo',
            })

        try:
            contato = RamalContato(
                unidade_id=form_data['unidade'] or None,
                tipo=form_data['tipo'],
                setor=form_data['setor'],
                nome=form_data['nome'],
                cargo_funcao=form_data['cargo_funcao'],
                ramal=form_data['ramal'],
                telefone=form_data['telefone'],
                celular=form_data['celular'],
                whatsapp=form_data['whatsapp'],
                email=form_data['email'],
                localizacao=form_data['localizacao'],
                observacao=form_data['observacao'],
                ativo=form_data['ativo'],
                ordem=ordem,
            )

            contato.full_clean()
            contato.save()

            registrar_auditoria_ramal(
                request=request,
                contato=contato,
                acao='criado',
                titulo=f'Ramal / contato criado: {contato.nome}'
            )

            messages.success(request, 'Ramal / contato cadastrado com sucesso.')
            return redirect('/portal/modulos/ramais-contatos/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível cadastrar o contato: {erro}')

    return render(request, 'ramais_contatos/formulario_ramal_contato.html', {
        'titulo': 'Novo ramal / contato',
        'subtitulo': 'Cadastre um novo ramal, contato interno, setor ou serviço.',
        'form_data': form_data,
        'unidades': unidades,
        'tipos': RamalContato.TIPO_CHOICES,
        'url_salvar': '/portal/modulos/ramais-contatos/novo/',
        'modo': 'novo',
    })


@login_required(login_url='/')
def editar_ramal_contato(request, contato_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_RAMAIS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_ramais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    contato = get_object_or_404(RamalContato, id=contato_id)
    unidades = Unidade.objects.filter(ativo=True).order_by('nome')
    form_data = contato_para_form_data(contato)

    if request.method == 'POST':
        form_data = montar_form_data_contato(request)

        erros = []

        if not form_data['nome']:
            erros.append('Informe o nome do contato, setor ou serviço.')

        if not form_data['tipo']:
            erros.append('Informe o tipo do contato.')

        try:
            ordem = int(form_data['ordem'] or 0)
        except ValueError:
            ordem = 0

        if erros:
            for erro in erros:
                messages.error(request, erro)

            return render(request, 'ramais_contatos/formulario_ramal_contato.html', {
                'titulo': 'Editar ramal / contato',
                'subtitulo': 'Atualize os dados do contato selecionado.',
                'form_data': form_data,
                'contato_editado': contato,
                'unidades': unidades,
                'tipos': RamalContato.TIPO_CHOICES,
                'url_salvar': f'/portal/modulos/ramais-contatos/editar/{contato.id}/',
                'modo': 'editar',
            })

        try:
            contato.unidade_id = form_data['unidade'] or None
            contato.tipo = form_data['tipo']
            contato.setor = form_data['setor']
            contato.nome = form_data['nome']
            contato.cargo_funcao = form_data['cargo_funcao']
            contato.ramal = form_data['ramal']
            contato.telefone = form_data['telefone']
            contato.celular = form_data['celular']
            contato.whatsapp = form_data['whatsapp']
            contato.email = form_data['email']
            contato.localizacao = form_data['localizacao']
            contato.observacao = form_data['observacao']
            contato.ativo = form_data['ativo']
            contato.ordem = ordem

            contato.full_clean()
            contato.save()

            registrar_auditoria_ramal(
                request=request,
                contato=contato,
                acao='alterado',
                titulo=f'Ramal / contato alterado: {contato.nome}'
            )

            messages.success(request, 'Ramal / contato atualizado com sucesso.')
            return redirect('/portal/modulos/ramais-contatos/')

        except ValidationError as erro:
            for mensagem in tratar_erros_validacao(erro):
                messages.error(request, mensagem)

        except Exception as erro:
            messages.error(request, f'Não foi possível atualizar o contato: {erro}')

    return render(request, 'ramais_contatos/formulario_ramal_contato.html', {
        'titulo': 'Editar ramal / contato',
        'subtitulo': 'Atualize os dados do contato selecionado.',
        'form_data': form_data,
        'contato_editado': contato,
        'unidades': unidades,
        'tipos': RamalContato.TIPO_CHOICES,
        'url_salvar': f'/portal/modulos/ramais-contatos/editar/{contato.id}/',
        'modo': 'editar',
    })


@login_required(login_url='/')
def inativar_ramal_contato(request, contato_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_RAMAIS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_ramais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    contato = get_object_or_404(RamalContato, id=contato_id)

    contato.ativo = False
    contato.save()

    registrar_auditoria_ramal(
        request=request,
        contato=contato,
        acao='alterado',
        titulo=f'Ramal / contato inativado: {contato.nome}'
    )

    messages.success(request, 'Ramal / contato inativado com sucesso.')
    return redirect('/portal/modulos/ramais-contatos/')


@login_required(login_url='/')
def reativar_ramal_contato(request, contato_id):
    if not usuario_pode_acessar_modulo(request.user, NOME_MODULO_RAMAIS):
        return render(request, 'core/sem_permissao.html', status=403)

    if not usuario_pode_gerenciar_ramais(request.user):
        return render(request, 'core/sem_permissao.html', status=403)

    contato = get_object_or_404(RamalContato, id=contato_id)

    contato.ativo = True
    contato.save()

    registrar_auditoria_ramal(
        request=request,
        contato=contato,
        acao='alterado',
        titulo=f'Ramal / contato reativado: {contato.nome}'
    )

    messages.success(request, 'Ramal / contato reativado com sucesso.')
    return redirect('/portal/modulos/ramais-contatos/')