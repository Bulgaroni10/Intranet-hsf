from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from modulos.models import Modulo
from core.models import NotificacaoUsuario
from core.services.notifications import criar_notificacao_usuario


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
