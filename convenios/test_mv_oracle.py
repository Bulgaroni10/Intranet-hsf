from unittest.mock import patch

from django.test import TestCase

from usuarios.models import Unidade
from .models import Convenio, PlanoConvenio, RegraAtendimentoConvenio
from .mv_oracle import IntegracaoMVErro, aplicar_convenios_planos, sincronizar_unidade


class SincronizacaoMVTests(TestCase):
    def setUp(self):
        self.unidade = Unidade.objects.create(nome='Hospital Teste', sigla='HT', codigo_mv=7)
        self.outra = Unidade.objects.create(nome='Outra', sigla='OU', codigo_mv=8)
        self.antigo = Convenio.objects.create(codigo_mv='99', nome='Convênio antigo')
        self.antigo.unidades.add(self.unidade)
        PlanoConvenio.objects.create(convenio=self.antigo, codigo_mv='1', nome='Plano antigo')

    def dados(self):
        return [{
            'codigo_convenio': '10',
            'nome_convenio': 'Convênio MV',
            'codigo_plano': '20',
            'nome_plano': 'Plano MV',
            'permissoes': {
                'sn_permite_ambulatorio': True,
                'sn_permite_externo': False,
                'sn_permite_homecare': False,
                'sn_permite_urgencia': True,
                'sn_permite_internacao': False,
            },
        }]

    def test_aplica_substituicao_atomica_da_unidade(self):
        resultado = aplicar_convenios_planos(self.unidade, self.dados())
        self.assertEqual(resultado['convenios'], 1)
        self.assertFalse(Convenio.objects.filter(pk=self.antigo.pk).exists())
        convenio = Convenio.objects.get(codigo_mv='10')
        self.assertTrue(convenio.unidades.filter(pk=self.unidade.pk).exists())
        regras = RegraAtendimentoConvenio.objects.filter(unidade=self.unidade)
        self.assertEqual(regras.count(), 6)
        self.assertEqual(regras.get(tipo_atendimento='pronto_atendimento').status, 'aceito')
        self.assertEqual(regras.get(tipo_atendimento='internacao').status, 'nao_aceito')

    def test_falha_na_consulta_preserva_dados(self):
        with patch('convenios.mv_oracle.consultar_convenios_planos', side_effect=IntegracaoMVErro('offline')):
            with self.assertRaises(IntegracaoMVErro):
                sincronizar_unidade(self.unidade)
        self.assertTrue(Convenio.objects.filter(pk=self.antigo.pk).exists())

    def test_dados_de_outra_unidade_nao_sao_excluidos(self):
        compartilhado = Convenio.objects.create(codigo_mv='55', nome='Compartilhado')
        compartilhado.unidades.add(self.outra)
        aplicar_convenios_planos(self.unidade, self.dados())
        self.assertTrue(Convenio.objects.filter(pk=compartilhado.pk).exists())

    def test_consolida_conflito_entre_codigo_e_nome_antigos(self):
        pelo_codigo = Convenio.objects.create(codigo_mv='10', nome='Nome antigo')
        pelo_codigo.unidades.add(self.unidade, self.outra)
        pelo_nome = Convenio.objects.create(codigo_mv='999', nome='Convênio MV')
        pelo_nome.unidades.add(self.unidade, self.outra)

        aplicar_convenios_planos(self.unidade, self.dados())

        atualizado = Convenio.objects.get(nome='Convênio MV')
        self.assertEqual(atualizado.codigo_mv, '10')
        self.assertTrue(atualizado.unidades.filter(pk=self.unidade.pk).exists())
        self.assertFalse(pelo_codigo.unidades.filter(pk=self.unidade.pk).exists())
        self.assertTrue(pelo_codigo.unidades.filter(pk=self.outra.pk).exists())
