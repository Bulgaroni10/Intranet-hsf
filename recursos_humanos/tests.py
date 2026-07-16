from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Setor, Unidade, Usuario
from .models import AnexoRH, SolicitacaoRH


class RecursosHumanosTests(TestCase):
    def setUp(self):
        self.u1 = Unidade.objects.create(nome='Unidade A', sigla='UA')
        self.u2 = Unidade.objects.create(nome='Unidade B', sigla='UB')
        self.setor = Setor.objects.create(nome='Recepção')
        self.usuario = Usuario.objects.create_user(username='pessoa', password='123', unidade=self.u1, setor=self.setor)
        grupo = Group.objects.create(name='RH')
        self.rh1 = Usuario.objects.create_user(username='rh1', password='123', unidade=self.u1, setor=self.setor)
        self.rh2 = Usuario.objects.create_user(username='rh2', password='123', unidade=self.u2, setor=self.setor)
        self.rh1.groups.add(grupo); self.rh2.groups.add(grupo)

    def criar(self):
        return SolicitacaoRH.objects.create(
            unidade=self.u1, setor=self.setor, solicitante=self.usuario,
            tipo='beneficios', assunto='Vale transporte', descricao='Solicitação teste.',
        )

    def test_usuario_cria_com_anexo(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse('rh_nova'), {
            'tipo': 'beneficios', 'assunto': 'Vale transporte', 'setor': self.setor.pk,
            'descricao': 'Solicitação teste.',
            'anexos': SimpleUploadedFile('ficha.pdf', b'pdf', content_type='application/pdf'),
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(AnexoRH.objects.count(), 1)

    def test_rh_de_outra_unidade_nao_visualiza(self):
        item = self.criar(); self.client.force_login(self.rh2)
        self.assertEqual(self.client.get(reverse('rh_detalhe', args=[item.pk])).status_code, 404)

    def test_usuario_nao_visualiza_solicitacao_de_outro(self):
        item = self.criar()
        outro = Usuario.objects.create_user(username='outro', password='123', unidade=self.u1, setor=self.setor)
        self.client.force_login(outro)
        self.assertEqual(self.client.get(reverse('rh_detalhe', args=[item.pk])).status_code, 404)

    def test_rh_da_unidade_atende(self):
        item = self.criar(); self.client.force_login(self.rh1)
        resposta = self.client.post(reverse('rh_atender', args=[item.pk]), {'status': 'concluida', 'resposta_rh': 'Concluído.'})
        self.assertEqual(resposta.status_code, 302)
        item.refresh_from_db(); self.assertEqual(item.status, 'concluida')
