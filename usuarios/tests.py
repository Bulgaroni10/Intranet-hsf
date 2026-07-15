from django.contrib.auth import get_user_model
from django.test import TestCase

from solicitacoes_ti.models import SolicitacaoTI
from usuarios.escopo import aplicar_escopo_unidade
from usuarios.models import Unidade


class EscopoUnidadeTests(TestCase):
    def setUp(self):
        self.unidade_a = Unidade.objects.create(nome='Hospital A', sigla='HA')
        self.unidade_b = Unidade.objects.create(nome='Hospital B', sigla='HB')
        self.usuario = get_user_model().objects.create_superuser(
            'admin.escopo', email='admin@example.com', password='senha',
            unidade=self.unidade_a,
        )
        self.item_a = SolicitacaoTI.objects.create(
            titulo='Chamado A', descricao='A', unidade=self.unidade_a,
        )
        self.item_b = SolicitacaoTI.objects.create(
            titulo='Chamado B', descricao='B', unidade=self.unidade_b,
        )
        self.global_item = SolicitacaoTI.objects.create(
            titulo='Chamado global', descricao='Global', unidade=None,
        )

    def test_superusuario_tambem_respeita_unidade_ativa(self):
        itens = aplicar_escopo_unidade(SolicitacaoTI.objects.all(), self.usuario)

        self.assertQuerySetEqual(itens.order_by('id'), [self.item_a])

    def test_globais_so_entram_quando_solicitados_explicitamente(self):
        itens = aplicar_escopo_unidade(
            SolicitacaoTI.objects.all(), self.usuario, incluir_globais=True,
        )

        self.assertQuerySetEqual(
            itens.order_by('id'), [self.item_a, self.global_item],
        )

    def test_sem_unidade_ativa_retorna_vazio_por_padrao(self):
        self.usuario.unidade = None
        self.usuario.save(update_fields=['unidade'])

        itens = aplicar_escopo_unidade(SolicitacaoTI.objects.all(), self.usuario)

        self.assertFalse(itens.exists())
