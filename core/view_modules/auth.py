from .common import *
from django.utils.http import url_has_allowed_host_and_scheme


def home(request):
    if request.user.is_authenticated:
        return redirect('portal')

    return render(request, 'core/home.html')

@require_POST
def login_intranet(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'ok': False,
            'message': 'Requisição inválida.'
        }, status=400)

    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if not username or not password:
        return JsonResponse({
            'ok': False,
            'message': 'Preencha usuário e senha.'
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

    unidades_disponiveis = list(
        Unidade.objects.filter(
            Q(id=user.unidade_id) | Q(usuarios_autorizados=user), ativo=True,
        ).distinct().order_by('nome')
    )
    unidade_id = str(data.get('unidade_id', '')).strip()
    if len(unidades_disponiveis) > 1 and not unidade_id:
        return JsonResponse({
            'ok': True,
            'requires_unit_selection': True,
            'message': 'Selecione a empresa que deseja acessar.',
            'unidades': [
                {'id': unidade.id, 'nome': unidade.nome, 'sigla': unidade.sigla}
                for unidade in unidades_disponiveis
            ],
        })

    if unidade_id:
        unidade_selecionada = next(
            (unidade for unidade in unidades_disponiveis if str(unidade.id) == unidade_id), None,
        )
        if unidade_selecionada is None:
            return JsonResponse({
                'ok': False,
                'message': 'Você não possui acesso à empresa selecionada.',
            }, status=403)
    else:
        unidade_selecionada = unidades_disponiveis[0]

    login(request, user)
    request.session['unidade_id'] = unidade_selecionada.id

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
            'unidade': unidade_selecionada.nome,
            'unidade_sigla': unidade_selecionada.sigla,
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


@login_required(login_url='/')
@require_POST
def selecionar_unidade_ativa(request):
    unidade_id = request.POST.get('unidade_id', '').strip()
    unidade = request.user.unidades_permitidas.filter(id=unidade_id, ativo=True).first()

    if unidade is None and str(request.user.unidade_id) == unidade_id:
        unidade = request.user.unidade

    if unidade is None:
        messages.error(request, 'Você não possui acesso à empresa selecionada.')
        return redirect('portal')

    request.session['unidade_id'] = unidade.id
    request.session.modified = True
    messages.success(request, f'Empresa ativa alterada para {unidade.sigla}.')

    destino = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        destino = '/portal/'

    return redirect(destino)
