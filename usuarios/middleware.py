from .models import Unidade


class UnidadeAtivaMiddleware:
    """Aplica à instância do usuário a unidade escolhida nesta sessão."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user and user.is_authenticated:
            permitidas = user.unidades_permitidas.filter(ativo=True)
            unidade_id = request.session.get('unidade_id')
            unidade_ativa = permitidas.filter(id=unidade_id).first()

            if unidade_ativa is None:
                unidade_ativa = permitidas.filter(id=user.unidade_id).first() or permitidas.first()

            if unidade_ativa is None and user.unidade_id:
                unidade_ativa = Unidade.objects.filter(id=user.unidade_id, ativo=True).first()

            if unidade_ativa:
                request.session['unidade_id'] = unidade_ativa.id
                user.unidade = unidade_ativa
            else:
                request.session.pop('unidade_id', None)

        return self.get_response(request)
