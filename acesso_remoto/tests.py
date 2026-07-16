from datetime import timedelta

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Setor, Unidade, Usuario
from .models import AnexoAcessoRemoto, SolicitacaoAcessoRemoto


class AcessoRemotoTests(TestCase):
    def setUp(self):
        self.u1 = Unidade.objects.create(nome='Unidade A', sigla='UA')
        self.u2 = Unidade.objects.create(nome='Unidade B', sigla='UB')
        self.s1 = Setor.objects.create(nome='Recepção')
        self.s2 = Setor.objects.create(nome='TI B')
        self.usuario = Usuario.objects.create_user(username='solicitante', password='teste123', unidade=self.u1, setor=self.s1)
        grupo = Group.objects.create(name='TI Suporte')
        self.ti_a = Usuario.objects.create_user(username='tia', password='teste123', unidade=self.u1, setor=self.s1)
        self.ti_b = Usuario.objects.create_user(username='tib', password='teste123', unidade=self.u2, setor=self.s2)
        self.ti_a.groups.add(grupo)
        self.ti_b.groups.add(grupo)

    def criar(self):
        agora = timezone.now()
        return SolicitacaoAcessoRemoto.objects.create(
            unidade=self.u1, setor=self.s1, solicitante=self.usuario, nome='Pessoa Teste',
            cpf='12345678909', email='pessoa@hospital.local', vinculo='colaborador',
            tipo_acesso='vpn', equipamento='P000123', sistema_destino='MV',
            finalidade='Plantão remoto', inicio_validade=agora,
            fim_validade=agora + timedelta(days=1),
        )

    def test_usuario_cria_solicitacao_com_anexo(self):
        self.client.force_login(self.usuario)
        inicio = timezone.localtime().strftime('%Y-%m-%dT%H:%M')
        fim = (timezone.localtime() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        resposta = self.client.post(reverse('acesso_remoto_nova'), {
            'nome': 'Pessoa Teste', 'cpf': '12345678909', 'email': 'pessoa@hospital.local',
            'vinculo': 'colaborador', 'setor': self.s1.pk, 'tipo_acesso': 'vpn',
            'equipamento': 'P000123', 'sistema_destino': 'MV',
            'finalidade': 'Plantão', 'inicio_validade': inicio, 'fim_validade': fim,
            'anexos': SimpleUploadedFile('termo.pdf', b'pdf', content_type='application/pdf'),
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(SolicitacaoAcessoRemoto.objects.count(), 1)
        self.assertEqual(AnexoAcessoRemoto.objects.count(), 1)

    def test_ti_nao_visualiza_ou_atende_outra_unidade(self):
        item = self.criar()
        self.client.force_login(self.ti_b)
        self.assertEqual(self.client.get(reverse('acesso_remoto_detalhe', args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('acesso_remoto_atender', args=[item.pk]), {'status': 'ativa'}).status_code, 404)

    def test_anexo_protegido_por_unidade(self):
        item = self.criar()
        anexo = AnexoAcessoRemoto.objects.create(
            solicitacao=item, arquivo=SimpleUploadedFile('termo.pdf', b'pdf'),
            nome_original='termo.pdf', enviado_por=self.usuario,
        )
        self.client.force_login(self.ti_b)
        self.assertEqual(self.client.get(reverse('acesso_remoto_anexo', args=[anexo.pk])).status_code, 403)

    def test_ti_da_unidade_atualiza_status(self):
        item = self.criar()
        self.client.force_login(self.ti_a)
        resposta = self.client.post(reverse('acesso_remoto_atender', args=[item.pk]), {
            'status': 'ativa', 'observacao_ti': 'VPN configurada.',
        })
        self.assertEqual(resposta.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, 'ativa')
