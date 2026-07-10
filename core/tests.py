import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from modulos.models import Modulo
from core.models import FavoritoModulo, NotificacaoUsuario
from core.services.dashboard import buscar_resumo_chamados_ti
from core.services.notifications import criar_notificacao_usuario
from solicitacoes_ti.models import SolicitacaoTI
from usuarios.models import Unidade


class ConveniosRoutingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="usuario.teste",
            password="senha-segura",
        )
        self.modulo = Modulo.objects.create(
            nome="MV / Sistema Hospitalar",
            categoria="assistencial",
            link=reverse("modulo_mv"),
        )

    def test_urls_legadas_redirecionam_para_url_canonica(self):
        self.client.force_login(self.user)

        for nome in ("convenios_legacy", "convenios_legacy_curta"):
            resposta = self.client.get(reverse(nome))
            self.assertRedirects(
                resposta,
                reverse("mv_convenios"),
                fetch_redirect_response=False,
            )

    def test_usuario_sem_grupo_permitido_recebe_403(self):
        grupo = Group.objects.create(name="Acesso MV restrito")
        self.modulo.grupos_permitidos.add(grupo)
        self.client.force_login(self.user)

        resposta = self.client.get(reverse("mv_convenios"))

        self.assertEqual(resposta.status_code, 403)

    def test_usuario_autorizado_abre_url_canonica(self):
        grupo = Group.objects.create(name="Acesso MV")
        self.modulo.grupos_permitidos.add(grupo)
        self.user.groups.add(grupo)
        self.client.force_login(self.user)

        resposta = self.client.get(reverse("mv_convenios"))

        self.assertEqual(resposta.status_code, 200)


class NotificacoesUsuarioTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.usuario_a = User.objects.create_user('usuario.a', password='senha')
        self.usuario_b = User.objects.create_user('usuario.b', password='senha')
        self.notificacao_a, _ = criar_notificacao_usuario(
            usuario=self.usuario_a,
            titulo='Mensagem A',
            origem='teste',
            objeto_id='1',
        )
        criar_notificacao_usuario(
            usuario=self.usuario_b,
            titulo='Mensagem B',
            origem='teste',
            objeto_id='1',
        )

    def test_listagem_retorna_somente_notificacoes_do_usuario(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse('api_listar_notificacoes'))
        dados = resposta.json()
        self.assertEqual(dados['nao_lidas'], 1)
        self.assertEqual([item['titulo'] for item in dados['notificacoes']], ['Mensagem A'])

    def test_usuario_nao_marca_notificacao_de_outro_usuario(self):
        notificacao_b = NotificacaoUsuario.objects.get(usuario=self.usuario_b)
        self.client.force_login(self.usuario_a)
        resposta = self.client.post(
            reverse('api_marcar_notificacao_lida', args=[notificacao_b.id])
        )
        self.assertEqual(resposta.status_code, 404)

    def test_criacao_idempotente_e_marcacao_como_lida(self):
        _, criada = criar_notificacao_usuario(
            usuario=self.usuario_a,
            titulo='Mensagem repetida',
            origem='teste',
            objeto_id='1',
        )
        self.assertFalse(criada)
        self.assertEqual(NotificacaoUsuario.objects.filter(usuario=self.usuario_a).count(), 1)

        self.client.force_login(self.usuario_a)
        resposta = self.client.post(
            reverse('api_marcar_notificacao_lida', args=[self.notificacao_a.id])
        )
        self.assertEqual(resposta.json()['nao_lidas'], 0)


class DashboardChamadosPermissoesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.unidade_a = Unidade.objects.create(nome='Unidade A', sigla='UA')
        self.unidade_b = Unidade.objects.create(nome='Unidade B', sigla='UB')
        self.comum_a = User.objects.create_user('comum.a', unidade=self.unidade_a)
        self.outro_a = User.objects.create_user('outro.a', unidade=self.unidade_a)
        self.outro_b = User.objects.create_user('outro.b', unidade=self.unidade_b)
        self.ti_a = User.objects.create_user('tecnico.a', unidade=self.unidade_a)
        grupo_ti = Group.objects.create(name='TI')
        self.ti_a.groups.add(grupo_ti)
        for usuario, titulo in (
            (self.comum_a, 'Próprio'), (self.outro_a, 'Mesma unidade'),
            (self.outro_b, 'Outra unidade'),
        ):
            SolicitacaoTI.objects.create(
                titulo=titulo, descricao='Teste', solicitante=usuario,
                unidade=usuario.unidade,
            )

    def test_usuario_comum_ve_somente_os_proprios_chamados(self):
        resumo = buscar_resumo_chamados_ti(self.comum_a)
        self.assertEqual(resumo['total_chamados_ti'], 1)
        self.assertEqual(resumo['ultimos_chamados_ti'][0].titulo, 'Próprio')

    def test_ti_ve_todos_da_unidade_e_nenhum_de_outra(self):
        resumo = buscar_resumo_chamados_ti(self.ti_a)
        titulos = set(resumo['ultimos_chamados_ti'].values_list('titulo', flat=True))
        self.assertEqual(titulos, {'Próprio', 'Mesma unidade'})
        self.assertEqual(resumo['total_chamados_ti'], 2)


class LoginUnidadeEFavoritosTests(TestCase):
    def setUp(self):
        self.unidade = Unidade.objects.create(nome='Hospital Teste', sigla='HT')
        self.user = get_user_model().objects.create_user(
            'login.teste', password='senha-segura', unidade=self.unidade,
        )
        self.modulo = Modulo.objects.create(
            nome='Módulo Teste', categoria='administrativo', link='/teste/',
        )

    def test_login_sem_seletor_define_unidade_na_sessao(self):
        resposta = self.client.post(
            reverse('login_intranet'),
            data=json.dumps({'username': 'login.teste', 'password': 'senha-segura'}),
            content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.client.session['unidade_id'], self.unidade.id)

    def test_favorito_alterna_e_e_individual(self):
        self.client.force_login(self.user)
        url = reverse('alternar_favorito_modulo', args=[self.modulo.id])
        resposta = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(resposta.json()['favorito'])
        self.assertTrue(FavoritoModulo.objects.filter(usuario=self.user, modulo=self.modulo).exists())

        resposta = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertFalse(resposta.json()['favorito'])
        self.assertFalse(FavoritoModulo.objects.filter(usuario=self.user, modulo=self.modulo).exists())
