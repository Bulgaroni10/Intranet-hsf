from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Unidade
from .models import DocumentoProtocolo
from .views import buscar_documentos_para_gestao


class IsolamentoDocumentosTests(TestCase):
    def setUp(self):
        self.unidade_a = Unidade.objects.create(nome='Hospital A', sigla='HA')
        self.unidade_b = Unidade.objects.create(nome='Hospital B', sigla='HB')
        self.usuario = get_user_model().objects.create_superuser(
            'admin.documentos', email='docs@example.com', password='senha',
            unidade=self.unidade_a,
        )
        self.documento_a = DocumentoProtocolo.objects.create(
            titulo='Documento A', unidade=self.unidade_a,
            arquivo='documentos/a.pdf',
        )
        self.documento_b = DocumentoProtocolo.objects.create(
            titulo='Documento B', unidade=self.unidade_b,
            arquivo='documentos/b.pdf',
        )
        self.client.force_login(self.usuario)

    def test_gestao_superusuario_respeita_unidade_ativa(self):
        documentos = buscar_documentos_para_gestao(self.usuario)

        self.assertIn(self.documento_a, documentos)
        self.assertNotIn(self.documento_b, documentos)

    def test_edicao_direta_de_outra_unidade_retorna_404(self):
        resposta = self.client.get(
            reverse('editar_documento_protocolo', args=[self.documento_b.id]),
        )

        self.assertEqual(resposta.status_code, 404)
