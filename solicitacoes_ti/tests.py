from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Unidade
from .models import SolicitacaoTI


class IsolamentoSolicitacoesTITests(TestCase):
    def setUp(self):
        self.unidade_a = Unidade.objects.create(nome='Hospital A', sigla='HA')
        self.unidade_b = Unidade.objects.create(nome='Hospital B', sigla='HB')
        self.usuario = get_user_model().objects.create_superuser(
            'admin.ti', email='ti@example.com', password='senha',
            unidade=self.unidade_a,
        )
        self.chamado_a = SolicitacaoTI.objects.create(
            titulo='Chamado da unidade A', descricao='A', unidade=self.unidade_a,
        )
        self.chamado_b = SolicitacaoTI.objects.create(
            titulo='Chamado da unidade B', descricao='B', unidade=self.unidade_b,
        )
        self.client.force_login(self.usuario)

    def test_lista_nao_expoe_chamado_de_outra_unidade(self):
        resposta = self.client.get(reverse('solicitacoes_ti'))

        self.assertContains(resposta, self.chamado_a.titulo)
        self.assertNotContains(resposta, self.chamado_b.titulo)

    def test_url_direta_de_outra_unidade_retorna_404(self):
        resposta = self.client.get(
            reverse('detalhe_solicitacao_ti', args=[self.chamado_b.id]),
        )

        self.assertEqual(resposta.status_code, 404)

    def test_atendimento_direto_de_outra_unidade_retorna_404(self):
        resposta = self.client.get(
            reverse('atender_solicitacao_ti', args=[self.chamado_b.id]),
        )

        self.assertEqual(resposta.status_code, 404)
