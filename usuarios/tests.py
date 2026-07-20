from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from solicitacoes_ti.models import SolicitacaoTI
from usuarios.escopo import aplicar_escopo_unidade
from usuarios.models import Setor, Unidade


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


class AdministracaoUnidadesSetoresTests(TestCase):
    def setUp(self):
        self.unidade = Unidade.objects.create(nome='Hospital Original', sigla='HORG')
        self.setor = Setor.objects.create(nome='Setor Original')
        self.admin = get_user_model().objects.create_superuser(
            'admin.cadastros', email='admin-cadastros@example.com', password='senha',
            unidade=self.unidade, setor=self.setor,
        )
        self.client.force_login(self.admin)

    def test_edita_nome_da_unidade_e_setor(self):
        resposta_unidade = self.client.post(reverse('editar_unidade', args=[self.unidade.pk]), {
            'nome': 'Hospital Atualizado', 'sigla': 'HORG', 'ativo': 'on',
        })
        resposta_setor = self.client.post(reverse('editar_setor', args=[self.setor.pk]), {
            'nome': 'Setor Atualizado', 'ativo': 'on',
        })
        self.assertEqual(resposta_unidade.status_code, 302)
        self.assertEqual(resposta_setor.status_code, 302)
        self.unidade.refresh_from_db()
        self.setor.refresh_from_db()
        self.assertEqual(self.unidade.nome, 'Hospital Atualizado')
        self.assertEqual(self.setor.nome, 'Setor Atualizado')

    def test_exclui_unidade_e_setor_sem_vinculos(self):
        unidade = Unidade.objects.create(nome='Unidade Temporária', sigla='UTEMP')
        setor = Setor.objects.create(nome='Setor Temporário')
        self.assertEqual(self.client.post(reverse('excluir_unidade', args=[unidade.pk])).status_code, 302)
        self.assertEqual(self.client.post(reverse('excluir_setor', args=[setor.pk])).status_code, 302)
        self.assertFalse(Unidade.objects.filter(pk=unidade.pk).exists())
        self.assertFalse(Setor.objects.filter(pk=setor.pk).exists())

    def test_bloqueia_exclusao_de_cadastros_com_vinculos(self):
        self.assertEqual(self.client.post(reverse('excluir_unidade', args=[self.unidade.pk])).status_code, 302)
        self.assertEqual(self.client.post(reverse('excluir_setor', args=[self.setor.pk])).status_code, 302)
        self.assertTrue(Unidade.objects.filter(pk=self.unidade.pk).exists())
        self.assertTrue(Setor.objects.filter(pk=self.setor.pk).exists())

    def test_exclusao_exige_post_e_permissao_administrativa(self):
        unidade = Unidade.objects.create(nome='Unidade Temporária', sigla='UTEMP2')
        self.assertEqual(self.client.get(reverse('excluir_unidade', args=[unidade.pk])).status_code, 405)
        usuario = get_user_model().objects.create_user('usuario.comum', password='senha')
        self.client.force_login(usuario)
        self.assertEqual(self.client.post(reverse('excluir_unidade', args=[unidade.pk])).status_code, 403)
        self.assertTrue(Unidade.objects.filter(pk=unidade.pk).exists())
