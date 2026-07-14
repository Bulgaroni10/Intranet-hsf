import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from modulos.models import Modulo
from core.models import FavoritoModulo, NotificacaoUsuario
from core.services.dashboard import buscar_resumo_chamados_ti
from core.services.notifications import criar_notificacao_usuario
from solicitacoes_ti.models import SolicitacaoTI
from usuarios.models import Unidade
from ramais_contatos.models import RamalContato
from core.services.search import buscar_global
from core.services.noc import montar_contexto_noc
from inventario_ti.models import ComputadorInventario
from django.utils import timezone
from convenios.models import (
    Convenio,
    Especialidade,
    PlanoConvenio,
    ProcedimentoProibidoPlano,
    RegraAtendimentoConvenio,
)


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


class FiltrosRegrasConveniosTests(TestCase):
    def setUp(self):
        self.unidade = Unidade.objects.create(nome='Hospital Filtro', sigla='HF')
        self.outra_unidade = Unidade.objects.create(nome='Outro Hospital', sigla='OH')
        self.user = get_user_model().objects.create_user(
            username='filtro.mv', password='senha', unidade=self.unidade,
        )
        Modulo.objects.create(
            nome='MV / Sistema Hospitalar', categoria='assistencial',
            link=reverse('modulo_mv'),
        )
        self.convenio = Convenio.objects.create(codigo_mv='10', nome='Convênio Filtro')
        self.convenio.unidades.add(self.unidade)
        self.plano = PlanoConvenio.objects.create(
            convenio=self.convenio, codigo_mv='20', nome='Plano Filtro',
        )
        self.especialidade = Especialidade.objects.create(nome='Cardiologia')
        for status, tipo in (
            ('aceito', 'consulta'),
            ('nao_aceito', 'exame'),
            ('consultar_autorizacao', 'terapia'),
            ('suspenso', 'internacao'),
        ):
            RegraAtendimentoConvenio.objects.create(
                unidade=self.unidade, convenio=self.convenio, plano=self.plano,
                tipo_atendimento=tipo, status=status,
                especialidade=self.especialidade if status == 'aceito' else None,
            )
        # Duplicidade histórica exata: a listagem deve exibir apenas uma vez.
        RegraAtendimentoConvenio.objects.create(
            unidade=self.unidade, convenio=self.convenio, plano=self.plano,
            tipo_atendimento='consulta', status='aceito',
            especialidade=self.especialidade,
        )
        self.outro_convenio = Convenio.objects.create(codigo_mv='30', nome='Outro Convênio')
        self.outro_convenio.unidades.add(self.unidade, self.outra_unidade)
        self.outro_plano = PlanoConvenio.objects.create(
            convenio=self.outro_convenio, codigo_mv='40', nome='Outro Plano',
        )
        RegraAtendimentoConvenio.objects.create(
            unidade=self.unidade, convenio=self.outro_convenio, plano=self.outro_plano,
            tipo_atendimento='pediatria', status='aceito',
        )
        RegraAtendimentoConvenio.objects.create(
            unidade=self.outra_unidade, convenio=self.outro_convenio, plano=self.outro_plano,
            tipo_atendimento='consulta', status='aceito',
        )
        ProcedimentoProibidoPlano.objects.create(
            unidade=self.unidade, convenio=self.convenio, plano=self.plano,
            codigo_procedimento='123', descricao_procedimento='Procedimento proibido',
        )
        self.client.force_login(self.user)

    def test_cada_status_retorna_somente_as_regras_correspondentes(self):
        for status in ('aceito', 'nao_aceito', 'consultar_autorizacao', 'suspenso'):
            with self.subTest(status=status):
                resposta = self.client.get(reverse('mv_convenios'), {
                    'status': status,
                    'procedimento': '123',
                })
                regras = list(resposta.context['regras'])
                self.assertTrue(regras)
                self.assertTrue(all(regra.status == status for regra in regras))
                chaves = {
                    (
                        regra.unidade_id, regra.convenio_id, regra.plano_id,
                        regra.tipo_atendimento, regra.especialidade_id, regra.status,
                    )
                    for regra in regras
                }
                self.assertEqual(len(regras), len(chaves))
                self.assertFalse(resposta.context['proibicoes'].exists())

    def test_sem_status_mantem_consulta_de_proibicoes(self):
        resposta = self.client.get(reverse('mv_convenios'), {'procedimento': '123'})
        self.assertEqual(resposta.context['proibicoes'].count(), 1)

    def test_filtros_individuais_nao_duplicam_resultados(self):
        casos = (
            ({'busca': 'Convênio Filtro'}, 4),
            ({'convenio': str(self.convenio.id)}, 4),
            ({'plano': str(self.plano.id)}, 4),
            ({'tipo_atendimento': 'consulta'}, 1),
            ({'especialidade': str(self.especialidade.id)}, 1),
            ({'status': 'aceito'}, 2),
        )
        for parametros, quantidade in casos:
            with self.subTest(parametros=parametros):
                resposta = self.client.get(reverse('mv_convenios'), parametros)
                regras = list(resposta.context['regras'])
                chaves = [
                    (
                        regra.unidade_id, regra.convenio_id, regra.plano_id,
                        regra.tipo_atendimento, regra.especialidade_id, regra.status,
                    )
                    for regra in regras
                ]
                self.assertEqual(len(regras), quantidade)
                self.assertEqual(len(chaves), len(set(chaves)))

    def test_filtro_de_procedimento_nao_duplica_proibicoes(self):
        resposta = self.client.get(reverse('mv_convenios'), {'procedimento': '123'})
        ids = list(resposta.context['proibicoes'].values_list('id', flat=True))
        self.assertEqual(len(ids), 1)
        self.assertEqual(len(ids), len(set(ids)))

    def test_todos_os_filtros_juntos_retornam_uma_regra_unica(self):
        resposta = self.client.get(reverse('mv_convenios'), {
            'busca': 'Convênio Filtro',
            'procedimento': '123',
            'convenio': str(self.convenio.id),
            'plano': str(self.plano.id),
            'tipo_atendimento': 'consulta',
            'especialidade': str(self.especialidade.id),
            'status': 'aceito',
        })
        regras = list(resposta.context['regras'])
        self.assertEqual(len(regras), 1)
        self.assertEqual(regras[0].status, 'aceito')
        self.assertFalse(resposta.context['proibicoes'].exists())


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

    def test_sidebar_global_exige_login_e_renderiza_menu_unico(self):
        url = reverse('sidebar_global')
        resposta_anonima = self.client.get(url)
        self.assertEqual(resposta_anonima.status_code, 302)

        self.client.force_login(self.user)
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'class="gsf-sidebar"')
        self.assertContains(resposta, 'class="gsf-topbar"')
        self.assertContains(resposta, 'Dashboard')


class SelecaoEmpresaUsuarioTests(TestCase):
    def setUp(self):
        self.empresa_a = Unidade.objects.create(nome='Empresa A', sigla='EA')
        self.empresa_b = Unidade.objects.create(nome='Empresa B', sigla='EB')
        self.empresa_bloqueada = Unidade.objects.create(nome='Empresa Bloqueada', sigla='EX')
        self.usuario = get_user_model().objects.create_user(
            'empresa.usuario', password='senha', unidade=self.empresa_a,
        )
        self.usuario.unidades_permitidas.set([self.empresa_a, self.empresa_b])
        self.client.force_login(self.usuario)

    def test_usuario_troca_somente_para_empresa_autorizada(self):
        resposta = self.client.post(
            reverse('selecionar_unidade_ativa'),
            {'unidade_id': self.empresa_b.id, 'next': '/portal/'},
        )
        self.assertRedirects(resposta, '/portal/', fetch_redirect_response=False)
        self.assertEqual(self.client.session['unidade_id'], self.empresa_b.id)

    def test_empresa_nao_autorizada_e_bloqueada_no_servidor(self):
        self.client.post(
            reverse('selecionar_unidade_ativa'),
            {'unidade_id': self.empresa_bloqueada.id},
        )
        self.assertNotEqual(self.client.session.get('unidade_id'), self.empresa_bloqueada.id)

    def test_middleware_aplica_empresa_da_sessao_sem_alterar_cadastro(self):
        sessao = self.client.session
        sessao['unidade_id'] = self.empresa_b.id
        sessao.save()

        resposta = self.client.get(reverse('sidebar_global'))
        self.assertContains(resposta, 'EB')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.unidade_id, self.empresa_a.id)


class BuscaGlobalPermissoesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.factory = RequestFactory()
        self.unidade_a = Unidade.objects.create(nome='Busca A', sigla='BA')
        self.unidade_b = Unidade.objects.create(nome='Busca B', sigla='BB')
        self.usuario_a = User.objects.create_user('busca.a', unidade=self.unidade_a)
        self.usuario_b = User.objects.create_user('busca.b', unidade=self.unidade_b)
        RamalContato.objects.create(nome='Ramal secreto B', ramal='9999', unidade=self.unidade_b)
        SolicitacaoTI.objects.create(
            titulo='Chamado secreto B', descricao='segredo operacional',
            solicitante=self.usuario_b, unidade=self.unidade_b,
        )

    def _buscar(self, usuario, termo):
        request = self.factory.get('/portal/busca/', {'q': termo})
        request.user = usuario
        return buscar_global(request, termo)

    def test_usuario_nao_encontra_ramal_de_outra_unidade(self):
        self.assertEqual(self._buscar(self.usuario_a, '9999'), [])

    def test_usuario_nao_encontra_chamado_de_outro_usuario(self):
        self.assertEqual(self._buscar(self.usuario_a, 'segredo operacional'), [])

    def test_dono_encontra_seu_chamado(self):
        resultados = self._buscar(self.usuario_b, 'segredo operacional')
        self.assertEqual([item['tipo'] for item in resultados], ['Solicitação TI'])


class ExportacaoRamaisCSVTests(TestCase):
    def setUp(self):
        self.unidade_a = Unidade.objects.create(nome='CSV A', sigla='CA')
        self.unidade_b = Unidade.objects.create(nome='CSV B', sigla='CB')
        self.usuario = get_user_model().objects.create_user(
            'csv.usuario', unidade=self.unidade_a,
        )
        Modulo.objects.create(nome='Ramais e Contatos', link='/ramais/')
        RamalContato.objects.create(
            nome='Recepção A', setor='Recepção', ramal='100',
            unidade=self.unidade_a,
        )
        RamalContato.objects.create(
            nome='Contato B', setor='TI', ramal='999', unidade=self.unidade_b,
        )

    def test_csv_respeita_unidade_e_filtros_da_tela(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(
            reverse('exportar_ramais_csv'), {'busca': 'Recepção'},
        )
        conteudo = resposta.content.decode('utf-8-sig')

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('Recepção A', conteudo)
        self.assertNotIn('Contato B', conteudo)
        self.assertNotIn('999', conteudo)


class ArquivosEstaticosProducaoTests(TestCase):
    @override_settings(DEBUG=False)
    def test_javascript_do_login_e_servido_com_debug_desligado(self):
        resposta = self.client.get('/static/core/js/home.js')
        self.assertEqual(resposta.status_code, 200)


class PainelNOCTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.unidade_a = Unidade.objects.create(nome='NOC A', sigla='NA')
        self.unidade_b = Unidade.objects.create(nome='NOC B', sigla='NB')
        self.ti = User.objects.create_user('noc.ti', unidade=self.unidade_a)
        self.ti.groups.add(Group.objects.create(name='TI Suporte'))
        self.comum = User.objects.create_user('noc.comum', unidade=self.unidade_a)
        ComputadorInventario.objects.create(hostname='PC-A', unidade=self.unidade_a, ultimo_contato=timezone.now())
        ComputadorInventario.objects.create(hostname='PC-B', unidade=self.unidade_b, ultimo_contato=timezone.now())

    def test_ti_ve_apenas_computadores_da_sua_unidade(self):
        contexto = montar_contexto_noc(self.ti)
        self.assertEqual([pc.hostname for pc in contexto['computadores']], ['PC-A'])
        self.assertEqual(contexto['total_online'], 1)

    def test_usuario_comum_recebe_403(self):
        self.client.force_login(self.comum)
        self.assertEqual(self.client.get(reverse('painel_noc')).status_code, 403)

    def test_ti_acessa_noc(self):
        self.client.force_login(self.ti)
        resposta = self.client.get(reverse('painel_noc'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'PC-A')
        self.assertNotContains(resposta, 'PC-B')
        self.assertContains(resposta, 'class="noc-header"')
        self.assertNotContains(resposta, 'class="gsf-sidebar"')
        self.assertNotContains(resposta, 'core/js/home.js')
