from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from convenios.mv_oracle import IntegracaoMVErro
from convenios.models import SincronizacaoMVExecucao
from core.models import NotificacaoUsuario
from usuarios.models import Unidade


@override_settings(MV_SYNC_ENABLED=True)
class SincronizarConveniosMVCommandTests(TestCase):
    def setUp(self):
        self.unidade = Unidade.objects.create(nome='Hospital Teste', sigla='HT', codigo_mv=7)
        self.outra = Unidade.objects.create(nome='Outro Hospital', sigla='OH', codigo_mv=8)
        grupo = Group.objects.create(name='TI')
        self.tecnico = get_user_model().objects.create_user('tecnico', unidade=self.unidade)
        self.tecnico.groups.add(grupo)
        self.outro_tecnico = get_user_model().objects.create_user('outro', unidade=self.outra)
        self.outro_tecnico.groups.add(grupo)

    @patch('convenios.management.commands.sincronizar_convenios_mv.sincronizar_unidade')
    def test_falha_notifica_somente_ti_da_unidade(self, sincronizar):
        sincronizar.side_effect = IntegracaoMVErro('Oracle indisponível')

        with self.assertRaises(CommandError):
            call_command('sincronizar_convenios_mv', unidade='HT', stderr=StringIO())

        alerta = NotificacaoUsuario.objects.get(usuario=self.tecnico, origem='sincronizacao_mv')
        self.assertFalse(alerta.lida)
        self.assertIn('Oracle indisponível', alerta.descricao)
        self.assertFalse(NotificacaoUsuario.objects.filter(usuario=self.outro_tecnico).exists())
        execucao = SincronizacaoMVExecucao.objects.get(unidade=self.unidade)
        self.assertEqual(execucao.status, 'erro')
        self.assertIsNotNone(execucao.finalizado_em)

    @patch('convenios.management.commands.sincronizar_convenios_mv.sincronizar_unidade')
    def test_sucesso_resolve_alerta_anterior(self, sincronizar):
        alerta = NotificacaoUsuario.objects.create(
            usuario=self.tecnico, origem='sincronizacao_mv', objeto_id=str(self.unidade.pk),
            titulo='Falha', descricao='Erro antigo', tipo='danger',
        )
        sincronizar.return_value = {
            'convenios': 22, 'planos': 1469, 'regras': 8814, 'procedimentos': 2499,
        }

        saida = StringIO()
        call_command('sincronizar_convenios_mv', unidade='HT', stdout=saida)

        alerta.refresh_from_db()
        self.assertTrue(alerta.lida)
        self.assertIsNotNone(alerta.lida_em)
        self.assertIn('22 convênios', saida.getvalue())
        execucao = SincronizacaoMVExecucao.objects.get(unidade=self.unidade)
        self.assertEqual(execucao.status, 'sucesso')
        self.assertEqual(execucao.procedimentos, 2499)

    @patch('convenios.management.commands.sincronizar_convenios_mv.sincronizar_unidade')
    def test_ti_com_acesso_adicional_tambem_recebe_alerta(self, sincronizar):
        self.outro_tecnico.unidades_permitidas.add(self.unidade)
        sincronizar.side_effect = IntegracaoMVErro('Falha de teste')

        with self.assertRaises(CommandError):
            call_command('sincronizar_convenios_mv', unidade='HT', stderr=StringIO())

        self.assertTrue(NotificacaoUsuario.objects.filter(
            usuario=self.outro_tecnico, origem='sincronizacao_mv', lida=False,
        ).exists())
