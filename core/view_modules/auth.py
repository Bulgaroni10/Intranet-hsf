from .common import *


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
