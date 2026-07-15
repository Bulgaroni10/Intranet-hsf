from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Unidade
from .models import DocumentoConhecimento


class IsolamentoBaseConhecimentoTests(TestCase):
    def setUp(self):
        self.unidade_a = Unidade.objects.create(nome='Hospital A', sigla='HA')
        self.unidade_b = Unidade.objects.create(nome='Hospital B', sigla='HB')
        self.usuario = get_user_model().objects.create_superuser(
            'admin.base', email='base@example.com', password='senha',
            unidade=self.unidade_a,
        )
        self.documento_b = DocumentoConhecimento.objects.create(
            titulo='Conhecimento B', unidade=self.unidade_b,
        )
        self.client.force_login(self.usuario)

    def test_edicao_direta_de_outra_unidade_retorna_404(self):
        resposta = self.client.get(
            reverse('editar_documento_conhecimento', args=[self.documento_b.id]),
        )

        self.assertEqual(resposta.status_code, 404)
